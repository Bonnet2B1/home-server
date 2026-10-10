#!/bin/sh
# Verifications avant deploiement d AdGuard Home.
#
# Tout est en lecture seule. Aucun conteneur n est cree, arrete ou supprime.
# Aucun nom de conteneur n est utilise comme motif de suppression.
#
#
#   scp adguard/verif.sh <ADMIN-ACCOUNT>@<TAILNET-IP-EXIT-DIRECT>:/tmp/
#   ssh <ADMIN-ACCOUNT>@<TAILNET-IP-EXIT-DIRECT>
#   sh /tmp/verif.sh
#
# doas reclame un tty et le mot de passe. Lance ce script depuis une vraie
# session SSH interactive, pas depuis un pipe.

set -u

say() {
    printf '\n=== %s ===\n' "$*"
}

# ---------------------------------------------------------------- A. HOTE

say "A1. Image tailscale reparee presente ?"
# Attendu : la ligne existe. C est elle qui evite le piege 5 de logbook.md :
# sur le noyau Alpine, tailscaled refuse d installer ses regles de pare-feu
# avec l image officielle, qui pointe vers iptables-legacy.
doas docker image inspect local/tailscale-nft:1.102.5 \
    --format 'present, id {{.Id}}' 2>&1 | tail -2

say "A2. Compose et espace disque"
doas docker compose version 2>&1 | tail -1
df -h /var/lib/docker | tail -1

say "A3. Repertoire /opt/adguard deja pris ?"
# Attendu : absent. Si present, on s arrete, on ne remplace rien.
if [ -e /opt/adguard ]; then
    echo "ATTENTION : /opt/adguard existe deja"
    ls -la /opt/adguard
else
    echo "absent, bon pour un deploiement propre"
fi

say "A4. Un conteneur adguard tourne deja ?"
# Recherche par nom exact, jamais par motif. Un motif "tailscale" a deja
# detruit la voie 1 le 2026-10-01.
doas docker ps -a --format '{{.Names}}' 2>/dev/null \
    | grep -x -e adguard -e adguard-tailscale \
    || echo "aucun conteneur adguard, nom exact"

# ------------------------------------------------- B. PORT 53, VOIE 2

say "B1. Port 53 sortant depuis l espace reseau nym"
# Trafic NE dans le netns : il traverse la chaine output de nym, ou le
# superviseur n insere que sa regle 0x80000. Le reject port 53 de nym
# s applique donc. Attendu : refus.
# Ce test ne dit RIEN du trafic relaye des clients. Voir B2.
doas docker exec tunnel-nymvpn python3 -c '
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(5)
try:
    s.sendto(b"\x00", ("9.9.9.9", 53))
    print("ENVOYE sans erreur immediate (reponse attendue dans le vide)")
except Exception as e:
    print("refuse ou sans reponse :", type(e).__name__)
' 2>&1 | tail -3

say "B2. Amont DoH et DoT depuis l espace reseau nym"
# 443 et 853 ne sont pas refuses par nym. Ce sont donc les deux choix surs
# pour l amont d AdGuard quand la sortie est anonymisee.
# DoH : 200 attendu. DoT : connexion TLS etablie attendue.
doas docker exec tunnel-nymvpn sh -c \
    'curl -s -o /dev/null -w "DoH 443 vers quad9 : HTTP %{http_code}\n" --max-time 20 https://dns.quad9.net/dns-query' 2>&1 | tail -2
doas docker exec tunnel-nymvpn python3 -c '
import socket, ssl
try:
    s = socket.create_connection(("9.9.9.9", 853), timeout=10)
    c = ssl.create_default_context().wrap_socket(s, server_hostname="dns.quad9.net")
    print("DoT 853 vers quad9 : TLS etablie", c.version())
    c.close()
except Exception as e:
    print("DoT 853 echoue :", type(e).__name__, e)
' 2>&1 | tail -3

# ---------------------------------------------------- C. LE FAIT CLÉ

say "C1. Ordre reel des regles dans la chaine forward de nym"
# C est LA verification qui decide de la question du port 53 en relais.
#
# Si la regle "accept" du superviseur est AVANT le reject port 53, alors le
# trafic relaye des clients passe, et un amont en DNS classique fonctionnerait.
# Si elle est APRES, il est refuse et DoT/DoH devient obligatoire.
#
# nft liste dans l ordre d application. On lit donc l ordre reel.
doas docker exec tunnel-nymvpn nft list chain inet nym forward 2>&1 | tail -20

say "C2. Memes regles sur la chaine output, pour comparaison"
doas docker exec tunnel-nymvpn nft list chain inet nym output 2>&1 | tail -12

say "C3. Chaine input de nym : quelles interfaces sont acceptees ?"
# C est le test qui repond a la question "pourquoi pas brancher AdGuard
# directement dans netns-nymvpn".
#
# Nym pose policy drop sur input. Si aucune regle n accepte iif "tailscale0",
# alors une requete DNS venant du tailnet vers un service qui tournerait dans
# ce netns tombe sur le drop final. Le service serait injoignable, sans erreur
# visible : juste un delai.
#
# Attendu aujourd hui : seulement eth0 (wireguard + retour etabli).
doas docker exec tunnel-nymvpn nft list chain inet nym input 2>&1 | tail -20

say "C4. Le netns netns-nymvpn accepte-t-il des requetes entrantes sur tailscale0 ?"
# Recherche directe d une regle acceptee sur tailscale0 dans input.
if doas docker exec tunnel-nymvpn nft list chain inet nym input 2>/dev/null \
        | grep -q 'iif "tailscale0"'; then
    echo "OUI : une regle input accepte tailscale0"
    doas docker exec tunnel-nymvpn nft list chain inet nym input 2>/dev/null | grep 'iif "tailscale0"'
else
    echo "NON : aucun accept sur tailscale0 dans la chaine input"
    echo "=> un service ecouteur dans ce netns serait injoignable depuis le tailnet"
fi

# ------------------------------------------------------------ D. ETAT

say "D1. Les deux noeuds de sortie sont ils en ligne"
doas docker exec tailscale tailscale status 2>&1 | head -3
doas docker exec exit-nymvpn tailscale status 2>&1 | head -3

say "D2. Le tunnel nym est il reellement connecte"
# On regarde l etat du client, pas le health des conteneurs : logbook.md
# signale que les conteneurs disaient healthy avec le tunnel tombe.
doas docker exec tunnel-nymvpn nym-vpnc status --table-style blank 2>&1 | head -2

say "D3. DNS actuel sur l hote, avant tout changement"
# Point de reference pour comparer apres le deploiement.
cat /etc/resolv.conf
