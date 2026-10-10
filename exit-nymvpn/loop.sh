#!/bin/bash
# Boucle de feedback pour exit-nymvpn.
#
# Signal : l IP de sortie du client change-t-elle quand on selectionne
# l exit node, et le client atteint-t-il Internet ?
#
# CONTROLE : on teste d'abord <OLD-SERVER-NAME>, l exit node qui marche deja. Si le
# controle echoue, ce n est pas le serveur le fautif, c est la boucle.
# Sans ce controle, tout echec est attribuable au mauvais composant.
#
# DNS : on interroge une IP brute, pas un nom. Le resolv.conf du conteneur
# pointe vers <COLIMA-GATEWAY-IP>, l passerelle de Colima, qui est privee. Avec un
# exit node, ce nom ne se resout plus. Confondre ce DNS avec un probleme de
# relais fait perdre des heures.

set -u
C=ts-client
PROBE_IP=1.1.1.1   # utilise uniquement par dns_ok, en DNS brut, jamais en HTTPS

# IP de api.ipify.org resolue depuis l hote, hors du chemin du bug.
IPIFY_IP=$(dig +short api.ipify.org A | head -1)
if [ -z "$IPIFY_IP" ]; then
  echo "IMPOSSIBLE de resoudre api.ipify.org depuis l hote. Abandon." >&2
  exit 2
fi
echo "api.ipify.org = $IPIFY_IP (resolu depuis l hote)"

verdict() { printf '%-22s %s\n' "$1" "$2"; }

set_node() {
  docker exec "$C" tailscale set --exit-node="$1" >/dev/null 2>&1
  sleep 8
}

# Test 1 : DNS vers une IP brute, isole du resolver local.
dns_ok() {
  docker exec "$C" dig +short +time=4 +tries=1 "$PROBE_IP" >/dev/null 2>&1
}

# Test 2 : HTTP vers api.ipify.org avec le SNI correct. On ne peut pas viser
# 1.1.1.1 en HTTPS avec un nom invente : Cloudflare refuse le SNI et curl
# renvoie 000 meme quand le reseau fonctionne. Mesurer ici donnait un faux
# ROUGE, y compris sur l exit node connu comme fonctionnel.
http_code() {
  docker exec "$C" curl -s --max-time 20 -o /dev/null -w '%{http_code}' \
    --resolve "api.ipify.org:443:$IPIFY_IP" https://api.ipify.org/ 2>/dev/null
}

# Test 3 : IP de sortie reelle. --resolve evite le DNS : le nom est lie a une
# IP resolue une seule fois depuis l hote, donc cet appel teste le relais seul.
egress_ip() {
  docker exec "$C" curl -s --max-time 20 \
    --resolve "api.ipify.org:443:$IPIFY_IP" https://api.ipify.org/ 2>/dev/null
}

# L'image Tailscale est une Alpine 3.22.6 sans curl ni dig. Sans cette
# fonction, la boucle echoue sur un conteneur frais et l echec ressemble a un
# probleme de relais. On verifie d abord le conteneur, puis on installe les
# deux outils s ils manquent. Le telechargement exige le reseau de base, donc
# sans exit node.
ensure_client() {
  if ! docker inspect "$C" >/dev/null 2>&1; then
    echo "Le conteneur $C n existe pas. Lancez d abord : ./test-client.sh <CLE> exit-nymvpn" >&2
    exit 2
  fi
  if docker exec "$C" sh -c 'command -v curl >/dev/null 2>&1 && command -v dig >/dev/null 2>&1'; then
    return 0
  fi
  echo "Installation de curl et bind-tools dans $C (absents de l image Tailscale)."
  set_node ""
  if docker exec "$C" sh -c 'apk add --no-cache curl bind-tools >/dev/null 2>&1'; then
    return 0
  fi
  echo "ECHEC de l installation dans $C. Installez-les a la main :" >&2
  echo "  docker exec $C apk add --no-cache curl bind-tools" >&2
  exit 3
}

run_case() {
  local nom=$1
  set_node ""
  local base_ip base_dns base_http
  base_ip=$(egress_ip); base_dns=$(dns_ok && echo ok || echo fail)
  base_http=$(http_code)
  verdict "$nom / base IP" "${base_ip:-vide}"
  verdict "$nom / base DNS" "$base_dns"
  verdict "$nom / base HTTP" "$base_http"

  set_node "$nom"
  local n_ip n_dns n_http
  n_ip=$(egress_ip); n_dns=$(dns_ok && echo ok || echo fail)
  n_http=$(http_code)
  verdict "$nom / relais IP" "${n_ip:-vide}"
  verdict "$nom / relais DNS" "$n_dns"
  verdict "$nom / relais HTTP" "$n_http"

  # Le DNS du conteneur pointe vers la passerelle de Colima, <COLIMA-GATEWAY-IP>,
  # qui est une adresse privee hors de Nym. Avec un exit node, ce resolver
  # n est plus joignable, sur n'importe quel exit node. Ce n est donc pas un
  # signal du bug, on ne l compte pas.
  #
  # Le signal est l IP de sortie et le code HTTP.
  if [ "$n_http" = "200" ] && [ -n "$n_ip" ]; then
    if [ "$n_ip" = "$base_ip" ]; then
      verdict "$nom / VERDICT" "OR (relais possiblement actif : IP inchangee, voir note)"
    else
      verdict "$nom / VERDICT" "VERT (IP de sortie changee : $base_ip -> $n_ip)"
    fi
  else
    verdict "$nom / VERDICT" "ROUGE (aucun relais : HTTP $n_http, IP ${n_ip:-vide})"
  fi
}

ensure_client

echo "=== controle : <OLD-SERVER-NAME>, exit node connu comme fonctionnel ==="
run_case <OLD-SERVER-NAME>
echo
echo "=== cible : exit-nymvpn ==="
run_case exit-nymvpn

set_node ""