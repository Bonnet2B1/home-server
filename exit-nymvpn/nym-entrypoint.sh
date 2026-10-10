#!/bin/sh
set -e

mkdir -p /run/dbus /var/lib/dbus

# /run n est pas un tmpfs dans ce conteneur : le pid laisse par dbus survit
# a un redemarrage. dbus refuse alors de demarrer, le conteneur sort, la
# politique restart le relance, et il retombe sur le meme pid : boucle.
# On efface donc les restes avant de demarrer.
rm -f /run/dbus/pid /run/dbus/system_bus_socket

if [ ! -s /etc/machine-id ]; then
    dbus-uuidgen > /etc/machine-id
fi

dbus-daemon --system --fork --nopidfile

/usr/lib/polkit-1/polkitd >/var/log/polkitd.log 2>&1 &

i=0
while [ "$i" -lt 50 ]; do
    if [ -S /run/dbus/system_bus_socket ]; then
        break
    fi
    i=$((i + 1))
    sleep 0.2
done

/usr/local/bin/nym-vpnd "$@" &
VPND_PID=$!

shutdown() {
    log "arret du superviseur, signalement de nym-vpnd"
    kill -TERM "$VPND_PID" 2>/dev/null || true
    wait "$VPND_PID" 2>/dev/null || true
    exit 0
}
trap shutdown TERM INT

log() {
    printf '%s [superviseur] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

# tailscaled marque son propre trafic avec 0x80000 : plan de controle, relais DERP
# et echanges WireGuard entre pairs. Ce trafic doit sortir en direct, par eth0.
#
# Deux obstacles. Nym choisit ses priorites dynamiquement, juste avant celles de
# Tailscale, donc sa regle "lookup 333" capture le trafic 0x80000 vers le tunnel
# et passe avant la regle de Tailscale. Ensuite sa chaine output, en policy drop,
# refuse tout ce qui sort par eth0.
#
# Nym decale ses deux regles a chaque connexion, pour se placer juste avant
# Tailscale. Une priorite fixe ne tient pas. On lit donc la ou il s est installe
# et on se place une Unite en dessous, dans la table 1000 dediee.
# Ce trafic ne doit pas passer par le mixnet : la connexion longue duree du plan
# de controle y est coupee au bout de deux minutes et le noeud passe hors ligne.
#
# Le trafic RELAYE des clients porte 0x40000. Il ne correspond pas au masque
# 0xff0000, donc ces deux regles ne le touchent pas. Il transite par la chaine
# forward et continue de partir par le tunnel, comme avant.
#
# Nym reappliquant son pare-feu a chaque connexion, le superviseur reetablit
# les deux regles.
ts_egress() {
    gw=$(ip route show table main default 2>/dev/null | awk '{print $3; exit}')
    [ -n "$gw" ] || return 1
    ip route replace table 1000 default via "$gw" dev eth0 2>/dev/null || return 1

    # Nym s installe sur deux priorites consecutives, la plus basse en premier.
    # Il faut passer sous la plus basse, sinon sa regle 333 capture 0x80000.
    np=$(ip rule show 2>/dev/null | grep -E 'suppress_prefixlength 0|fwmark 0x14d lookup 333' |
         awk -F: '{print $1}' | sort -n | head -1)
    [ -n "$np" ] || return 1
    want=$((np - 1))

    # Nym intercepte TOUT le trafic non-Tailscale avec sa regle 333, et elle
    # passe avant la regle de Tailscale qui renvoie le subnet 100.64/10 vers
    # tailscale0. Un paquet du client vers un site part donc dans le tunnel,
    # mais surtout la REPONSE du site vers 100.64.0.0/10 part aussi dans le
    # tunnel : elle ressort par Nym au lieu de revenir au client, et le client
    # ne recoit jamais rien.
    # Il faut donc une regle qui renvoie le subnet vers tailscale0, placee
    # AVANT celle de Nym. Le masque de Tailscale est 0xff0000, donc le trafic
    # a 0x40000 n est pas touche.
    tsip=$(ip -4 addr show tailscale0 2>/dev/null | awk '/inet /{split($2,a,"/"); print a[1]; exit}')
    [ -n "$tsip" ] || return 1
    # Tailscale choisit son numero de table, 52 sur cette version, et sa regle
    # se lit exactement "from all lookup 52", sans fwmark et sans nom
    # d interface. On lit ce numero dans la regle, on ne le devine pas.
    # On ne peut pas chercher la table qui contient "dev tailscale0" : la
    # table 0 les montre toutes, donc elle matcherait en premier a tort.
    tstab=$(ip rule show 2>/dev/null |
            sed -nE 's/^[0-9]+:[[:space:]]+from all lookup ([0-9]+)$/\1/p' |
            head -1)
    [ -n "$tstab" ] || return 1
    want_ts=$((np - 2))
    cur_ts=$(ip rule show 2>/dev/null | grep -E 'lookup '"$tstab"'$' |
             grep '100.64.0.0/10' | awk -F: '{print $1; exit}')
    if [ "$cur_ts" != "$want_ts" ]; then
        if [ -n "$cur_ts" ]; then
            ip rule del priority "$cur_ts" 2>/dev/null
        fi
        ip rule add priority "$want_ts" to 100.64.0.0/10 lookup "$tstab" 2>/dev/null ||
            return 1
        log "retour vers les clients tailscale place en priorite $want_ts, avant Nym en $np"
    fi

    cur=$(ip rule show 2>/dev/null | grep -E '^[0-9]+:.*lookup 1000$' | awk -F: '{print $1; exit}')
    if [ "$cur" != "$want" ]; then
        if [ -n "$cur" ]; then
            ip rule del priority "$cur" 2>/dev/null
        fi
        ip rule add priority "$want" fwmark 0x80000/0xff0000 lookup 1000 2>/dev/null || return 1
        log "acces direct du trafic tailscale place en priorite $want, sous Nym en $np"
    fi

    if ! nft list chain inet nym output 2>/dev/null | grep -q 'meta mark.*0x0*80000'; then
        nft insert rule inet nym output oifname "eth0" meta mark 0x80000 accept ||
            return 1
        log "regle nft de sortie du trafic tailscale reinseree"
    fi

    # Nym est concu pour etre un client, pas une passerelle. Sa chaine input est
    # en policy drop et n accepte que lo, les reponses de ses propres passerelles
    # et iif tun0. Sans cette regle, tout le trafic de retour du sortie direct
    # arrive par eth0 et est drope, le noeud ne repond plus.
    # Seules les reponses a une connexion deja ouverte sont acceptees. Aucune
    # connexion entrante nouvelle ne l est, donc la politique reste fermee.
    if ! nft list chain inet nym input 2>/dev/null | grep -q 'iif "eth0" ct state'; then
        nft insert rule inet nym input iif "eth0" ct state established,related accept ||
            return 1
        log "regle nft de retour du trafic tailscale reinseree"
    fi

    # WireGuard utilise un seul port UDP. tailscaled l ouvre lui-meme, mais sans
    # annonce de point de terminaison, et rien ne le laisse entrer : la regle
    # ci-dessus ne l accepte pas, car le premier paquet d une connexion UDP
    # n a aucun etat et n est donc jamais "established". Le noeud se declare
    # alors sans point d acces, DERP ne le connait pas non plus, et il ne peut
    # plus rien relayer.
    #
    # Le port se lit dans Addrs, que tailscaled publie pour son propre noeud.
    # Le champ LocalPort n existe pas dans cette version. On prend la premiere
    # adresse qui porte un port, en ignorant le port 0 des adresses non
    # annoncees.
    # On interroge tailscaled par le socket partage en volume : chaque
    # conteneur a son propre espace de processus, donc ss, execute ici, ne
    # verrait pas tailscaled, meme si les deux partagent le meme espace
    # reseau. Le port change a chaque redemarrage, il faut le relire a chaque
    # boucle du superviseur.
    wg=$(TS_SOCKET=/var/run/tailscale/tailscaled.sock \
         tailscale status --json 2>/dev/null | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    sys.exit(1)
for a in (d.get("Self") or {}).get("Addrs") or []:
    p=a.rsplit(":", 1)
    if len(p) == 2 and p[1].isdigit() and int(p[1]):
        print(p[1]); break')
    [ -n "$wg" ] || return 1

    if ! nft list chain inet nym input 2>/dev/null | grep -q "udp dport $wg"; then
        nft insert rule inet nym input iif "eth0" udp dport "$wg" accept ||
            return 1
        log "regle nft d acces au wireguard tailscale reineree, port $wg"
    fi

    # tailscaled tourne avec TS_DEBUG_FIREWALL_MODE=auto parce que Nym possede
    # deja le pare-feu. Il n installe donc plus ses chaines ts-input, ts-forward
    # et ts-postrouting, et sans elles il ne fait aucun relai : le noeud est en
    # ligne mais ne route rien pour ses clients.
    # Ces trois equivalents sont ecrits ici, dans la table Nym.
    #
    # 1. Marquer 0x40000 le trafic entrant d un client, c est ainsi qu on le
    #    distingue du trafic propre a tailscaled, qui porte 0x80000.
    # 2. Autoriser le relais vers le tunnel, puis le retour du meme tunnel.
    #    Le reject final de Nym reste en place pour tout le reste.
    #
    # Pas de masquerade. La chaine NAT de Nym s appelle nat, il n existe aucune
    # chaine postrouting, et nat reste vide. Le relais n en a pas besoin : la
    # passerelle de sortie Nym NAT elle-meme, et la regle de retour
    # "to 100.64.0.0/10 lookup 52" route la reponse vers tailscale0.
    if ! nft list chain inet nym forward 2>/dev/null | grep -q 'meta mark set 0x00040000'; then
        nft insert rule inet nym forward iifname "tailscale0" meta mark set 0x00040000
        nft insert rule inet nym forward oifname "tun0" meta mark 0x00040000 accept
        nft insert rule inet nym forward iifname "tun0" oifname "tailscale0" ct state established,related accept
        nft insert rule inet nym forward oifname "tun0" ct state established,related accept
        log "regles de relais tailscale ecrites dans le pare-feu nym"
    fi
}

tunnel_state() {
    /usr/local/bin/nym-vpnc status --table-style blank 2>/dev/null | head -1
}

log "nym-vpnd demarre, pid $VPND_PID"

i=0
while [ "$i" -lt 150 ]; do
    if /usr/local/bin/nym-vpnc status >/dev/null 2>&1; then
        break
    fi
    if ! kill -0 "$VPND_PID" 2>/dev/null; then
        log "nym-vpnd est mort, le conteneur s arrete"
        wait "$VPND_PID"
        exit 1
    fi
    i=$((i + 1))
    sleep 2
done

if [ "$i" -ge 150 ]; then
    log "nym-vpnc ne repond pas apres 300 s, le conteneur s arrete"
    kill -TERM "$VPND_PID" 2>/dev/null || true
    exit 1
fi

if [ ! -s /var/lib/nym-vpnd/mainnet/mnemonic.json ]; then
    log "ATTENTION aucune mnemonic Nym, le tunnel ne peut pas s etablir"
fi

attempt=0
while true; do
    if ! kill -0 "$VPND_PID" 2>/dev/null; then
        log "nym-vpnd est mort, le conteneur s arrete"
        wait "$VPND_PID"
        exit 1
    fi

    state=$(tunnel_state)

    # ts_egress teste chaque element avant d agir, donc on peut l appeler
    # sans arret. Le superviseur la rappelle meme quand le tunnel vient de
    # se reconnecter, car Nym reconstruit ses chaines et les efface.
    ts_egress 2>/dev/null || true

    case "$state" in
        *Connected*)
            if [ "$attempt" -ne 0 ]; then
                log "tunnel etabli apres $attempt tentative(s)"
                attempt=0
            fi
            ;;
        *Connecting*|*Reconnecting*|*Registering*|*Resolving*|*Unregistering*)
            log "etat transitoire (${state:-inconnu}), attente"
            ;;
        *)
            attempt=$((attempt + 1))
            log "tunnel absent (${state:-inconnu}), tentative $attempt"
            /usr/local/bin/nym-vpnc connect >/dev/null 2>&1 || true
            ;;
    esac

    sleep 30
done
