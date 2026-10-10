#!/bin/sh
# Conteneur Tailscale servant de client de test pour exit-nymvpn.
# Il ne touche pas au Mac hote : seul le conteneur choisit l exit node.
# Le Mac reste sur exit-direct, donc la session de travail n est pas coupee.
#
# NET_ADMIN   : creer et configurer les interfaces reseau.
# /dev/net/tun : la porte vers le noyau, pour creer tailscale0.
set -eu

KEY="$1"
TARGET="$2"

echo "== arret de l ancien client =="
docker rm -f ts-client >/dev/null 2>&1 || true
sleep 2

echo "== demarrage du demon tailscaled =="
# tailscaled n accepte que quelques options. La cle ne se passe pas au
# demarrage, l enregistrement se fait avec "tailscale up" juste apres.
docker run -d --name ts-client \
    --cap-add=NET_ADMIN \
    --device=/dev/net/tun \
    tailscale/tailscale:stable \
    tailscaled \
        --state=mem:

sleep 4

echo "== enregistrement avec la cle =="
docker exec ts-client tailscale up \
    --authkey="$KEY" \
    --hostname=ts-test \
    --accept-dns=false \
    --accept-routes=true \
    2>&1 | head -6

echo "== attente de l IP =="
i=0
while [ "$i" -lt 40 ]; do
    sleep 3
    ip=$(docker exec ts-client tailscale ip -4 2>/dev/null || true)
    if [ -n "$ip" ]; then
        echo "enregistre, IP tailscale : $ip"
        break
    fi
    i=$((i + 1))
done

if [ -z "$(docker exec ts-client tailscale ip -4 2>/dev/null || true)" ]; then
    echo "ECHEC de l enregistrement, journal :"
    docker logs ts-client 2>&1 | tail -12
    exit 1
fi

echo "== le noeud est-il visible dans le tailnet ? =="
docker exec ts-client tailscale status 2>&1 | head -6

echo "== choix de exit-nymvpn comme exit node =="
docker exec ts-client tailscale set --exit-node="$TARGET"
sleep 10
echo "exit node actif : $(docker exec ts-client tailscale debug prefs 2>/dev/null | grep -i exitnodeid | tr -d '\t ')"