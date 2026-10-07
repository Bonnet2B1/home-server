# Runbook : serveur domestique sur laptop `<SERVER-MODEL>`

Ce document décrit l'état du projet et les procédures. Mettez-le à jour après chaque étape.

Il s'adresse aussi à un agent qui reprend le projet sans contexte. Pour lui, la section « État réel de la machine » est la seule source de vérité. Tout le reste est une intention, une décision ou une archive. Une case cochée décrit un travail fait, pas forcément un objet encore présent.

## État réel de la machine, vérifié le 2026-10-03

Cette section décrit ce qui existe réellement sur le serveur. Elle prime sur les autres sections du document. Vérifiez-la avant d'agir, elle peut être périmée.

| Élément | État | Emplacement |
|---|---|---|
| Alpine 3.24, nom d'hôte `<OLD-SERVER-NAME>` | présent | — |
| Docker 29.5.x, compose v5.1.4 | présents, démarrent au boot | — |
| Utilisateur `<ADMIN-ACCOUNT>` avec `doas` | présent | — |
| `<OLD-SERVER-NAME>`, exit node direct | en ligne, `<TAILNET-IP-EXIT-DIRECT>`, identité persistante | `/opt/tailscale`, conteneur `tailscale` |
| `<OLD-NODE-EXIT-NYMVPN>`, exit node anonymisé | en ligne, `<TAILNET-IP-EXIT-NYMVPN>`, tunnel Nym connecté | `/opt/tailscale-nym`, conteneurs `<OLD-NETNS>`, `nym`, `<OLD-NODE-EXIT-NYMVPN>` |
| NymVPN (ancien projet) | retiré le 2026-09-29 | `/opt/nymvpn` absent |
| Port `127.0.0.1:1090` | libre | — |
| Adaptateur USB-C vers RJ45, Realtek RTL8156 | en service comme `eth0`, `<LAN-IP-SERVER>`, 1 Gbit/s | port USB du PCH Intel |
| `ethtool` 7.0 et `ifupdown-ng-ethtool` | installés le 2026-10-05, binaires de diagnostic | — |
| `uplink-guard`, épinglage de la passerelle | en service le 2026-10-05, supervisé, runlevel `default` | `/usr/local/bin/uplink-guard`, `/etc/init.d/uplink-guard` |
| Sauvegardes de la configuration réseau | présentes | `/etc/network/interfaces.bak.202610052234`, `.bak.202610052137` |

Réévaluée le 2026-10-05 pour la partie réseau. Voir « Diagnostic du 2026-10-05 », qui vaut pour la sortie Internet, le Wi-Fi et l'Ethernet.

Les deux voies vivent sur le même hôte. La voie 1 tourne dans le réseau de l'hôte. La voie 2 tourne dans un espace réseau dédié, tenu par le conteneur `<OLD-NETNS>`. Un redémarrage de l'hôte remet les deux voies en ligne sans intervention : les conteneurs portent `restart: unless-stopped` et les identités vivent dans des volumes.

Causes racines trouvées le 2026-10-03 :

- Voie 1 : le compose montait le volume `state` mais ne posait pas `TS_STATE_DIR`. `containerboot` rangeait donc l'identité en mémoire. La suppression du conteneur a effacé l'identité, et aucune clé d'authentification ne restait pour la reconstruire. Voir « Incident ».
- Voie 2 : le superviseur écrivait sa règle de masquerade dans `inet nym postrouting`. Cette chaîne n'existe pas. La chaîne réelle s'appelle `nat`, et elle reste vide. L'écriture échouait en silence et journalisait un faux succès toutes les 30 secondes. Le relais n'a pas besoin de masquerade : la passerelle de sortie Nym NAT elle-même. Le bloc a été retiré.

## Incident du 2026-10-01 : perte de l'accès à la voie 1

L'agent a détruit l'accès au serveur. Pendant le nettoyage de la voie 2, il a lancé une commande trop large :

```sh
docker ps -a --format "{{.Names}}" | grep -Ei "nym|netns|tailscale" | while read n; do docker rm -f "$n"; done
```

Le motif `tailscale` a matché le conteneur de la voie 1, `tailscale`, dans `/opt/tailscale`, et l'a supprimé. Ce conteneur était la seule voie d'accès : le SSH passe par le tailnet, jamais par le réseau local. L'utilisateur n'avait aucun accès physique, et le reboot n'a pas rétabli le nœud.

État au 2026-10-01 :

- Le conteneur voie 1 a été recréé par `docker compose up -d` et il tourne.
- L'hôte a été redémarré.
- `<OLD-SERVER-NAME>` n'apparaît toujours pas dans le tailnet.
- La cause exacte n'est pas identifiée. Aucun journal n'a pu être lu pendant l'incident, faute de retour console. La suppression du conteneur est le déclencheur. Un autre objet, peut-être un résidu de la voie 2, peut entretenir la panne.

Piste écartée le 2026-10-03 : une perte de route ou de DNS de l'hôte, avec un `/etc/resolv.conf` pointant vers `100.100.100.100`, adresse servie par `tailscaled` lui-même. L'hôte répondait normalement. La vraie cause est décrite dans « Résolution ».

Reprise, à faire avec un accès physique ou distant :

1. Lire `docker ps -a` et le STATUS réel du conteneur.
2. Lire `cd /opt/tailscale && docker compose logs --tail 80`. Chercher `NeedsLogin`, `network is unreachable`, `no such host`, ou un `panic`.
3. Vérifier la route et le DNS de l'hôte : `ip -4 route`, `cat /etc/resolv.conf`, `ping -c2 1.1.1.1`.
4. Si `/etc/resolv.conf` pointe vers `100.100.100.100`, le remettre sur un résolveur public.
5. Recréer le conteneur : `cd /opt/tailscale && docker compose up -d --force-recreate`. L'état du nœud vit dans le volume `state` et survit.

Leçon : ne jamais piloter un `docker rm -f` par un motif de nom. Cibler un conteneur par son nom exact, ou laisser `docker compose down` agir projet par projet. La voie 1 et la voie 2 vivent sur le même hôte, donc un motif partagé frappe les deux.

### Résolution, 2026-10-03

L'accès distant est revenu par le réseau local. Le diagnostic a montré trois causes.

1. Le compose de la voie 1 montait le volume `state`, mais ne posait pas `TS_STATE_DIR`. `containerboot` démarrait donc avec `--state=mem:`, et l'identité du nœud vivait en mémoire. Chaque recréation du conteneur perdait l'identité.
2. Aucune clé d'authentification ne restait pour reconstruire l'identité.
3. `containerboot` donne 60 secondes à `tailscale up`. Sans clé, l'enregistrement attend une validation par URL. Le délai expire, `containerboot` arrête `tailscaled`, le conteneur sort avec le code 0, et `restart: unless-stopped` le relance. Chaque cycle produit une nouvelle URL. La boucle interdit toute connexion par URL.

Le correctif au compose pose `TS_STATE_DIR=/var/lib/tailscale` et `TS_AUTHKEY=${TS_AUTHKEY}`. La première rend l'identité persistante. La seconde enregistre le nœud immédiatement. La clé vit dans `/opt/tailscale/.env`, mode `600`.

Après le correctif, `tailscaled.state` apparaît dans le volume. Un `docker restart tailscale` laisse le nœud en ligne, avec la même adresse, et le journal affiche `machineAuthorized=true; authURL=false`.

L'ancien nœud `<OLD-SERVER-NAME>` a été supprimé dans la console. Le nouveau nœud a repris le nom `<OLD-SERVER-NAME>` et l'adresse `<TAILNET-IP-EXIT-DIRECT>`. L'ancienne adresse `<TAILNET-IP-OLD-IDENTITY>` ne sert plus.

## Diagnostic du 2026-10-05 : mise en service de l'Ethernet, correctif du flux ARP

Point de départ : l'utilisateur a acheté un adaptateur USB-C vers RJ45 et l'a branché sur le serveur. Il constate que le trafic sort par le Wi-Fi. Sa constatation est exacte.

### L'adaptateur est bon, et il était visible depuis le début

| Mesure | Valeur |
|---|---|
| Périphérique USB | `0bda:8156` « USB 10/100/1G/2.5G LAN », Realtek RTL8156, sur le port USB 3.x du PCH Intel (`pci 00:14.0`) |
| Pilote | `r8152` v1.12.13, chargé et lié depuis le boot de 18h27 |
| Interface | `eth0`, MAC `<MAC-ETH0>`, ifindex 2 |
| Négociation | 1 Gbit/s full duplex, `Link detected: yes`, `carrier` stable, 0 erreur physique |
| Bail DHCP | `<LAN-IP-SERVER>/24`, passerelle `<LAN-GATEWAY-IP>`, DNS `<LAN-GATEWAY-IP>`, 86400 s |

Le serveur n'a aucun port Ethernet intégré. L'adaptateur est donc la seule option filaire, et il fonctionne.

### Pourquoi il n'était pas utilisé

`/etc/network/interfaces` ne déclarait que `lo` et `wlan0`. Aucun bloc `eth0`. L'interface était donc administrativement down, sans adresse et sans route, et le DHCP n'était jamais lancé. Aucun réglage de l'interface ne pouvait changer cela : il fallait écrire la configuration. C'est fait, et conservé. Voir « Correctif retenu ».

### La vraie cause de l'instabilité est le Wi-Fi

Le lien sans fil change de bande tout seul. En quelques minutes, `iw dev wlan0 link` est passé de 5260 MHz (5 GHz, canal 52) à 2462 MHz (2.4 GHz, canal 11), puis est revenu sur 5 GHz, puis sur 2.4 GHz. Le signal est de -27 dBm. Ce n'est donc pas un problème de couverture.

La gigue qui en découle, mesurée vers `1.1.1.1` sur 30 paquets :

| Lien | min | moy | max | perte |
|---|---|---|---|---|
| Wi-Fi (`wlan0`) | 15,4 ms | **31,9 ms** | **69,5 ms** | 0 % |
| Ethernet (`eth0`, cible forcée) | 14,4 ms | **15,0 ms** | 15,6 ms | 0 % |

Le même phénomène se voit sur le tunnel tailnet, mesuré depuis le Mac : 16,7 / 28,2 / 70,5 ms, écart-type 18 ms. C'est la plainte « ça marche à peu près », quantifiée.

Deux aggravants, non corrigés :

- `iw reg get` renvoie `country 00: DFS-UNSET`, et **tous** les canaux sont en `PASSIVE-SCAN`. Le domaine réglementaire n'a jamais été posé. C'est un défaut connu avec le pilote `iwlwifi` de cette machine.
- `wpa_supplicant` tourne sous `supervise-daemon` avec `--respawn-max 5 --respawn-period 1800`. Au-delà de cinq redémarrages en 30 minutes, le superviseur renonce et le serveur se retrouve sans liaison.

Aucun de ces deux points n'a été corrigé. Les corriger impose une désassociation Wi-Fi, donc un risque de perte d'accès sur une machine sans accès physique.

### La cause racine : deux interfaces sur le même subnet (flux ARP)

Une fois `eth0` monté avec son bail DHCP, la route par défaut bascule seule vers `eth0` (ifupdown-ng donne le metric 200 à un lien filaire et 300 au Wi-Fi). Mais le trafic sortant se met alors à perdre des paquets **par bouffées** : des périodes bonnes suivies de périodes à 100 % de perte.

La cause n'est pas la `<ISP-BOX>`. Elle est côté noyau. Une capture le montre :

```text
eth0 :  <LAN-IP-SERVER> > 1.1.1.1   ICMP echo request
wlan0 : 1.1.1.1 > <LAN-IP-SERVER>   ICMP echo reply
```

La requête sort par le câble, la réponse revient par le Wi-Fi. Puis, en comptant les ARP :

| `arp_ignore` | demandes `.40` sur eth0 | **réponses `.40` sur eth0** | réponses `.40` sur wlan0 |
|---|---|---|---|
| 0 (défaut) | 3 | **0** | **2** |
| 1 | 5 | **0** | 0 |

Le serveur ne répond **jamais** à l'ARP pour `.40` sur `eth0`. Avec la valeur par défaut, il répond *sur `wlan0`*. La `<ISP-BOX>` associe donc `.40` à la MAC Wi-Fi, les retours arrivent par `wlan0`, et `rp_filter=1` les rejette. De là les bouffées.

`arp_ignore=1` ne corrige rien : il supprime la réponse sur `wlan0` sans la rétablir sur `eth0`. `arp_announce=2` est nuisible ici : il choisit « la meilleure adresse locale » d'après la route, qui pointe vers `wlan0`. Les deux sont restés aux valeurs par défaut.

Le déclencheur est l'ambiguïté de `<LAN-SUBNET>`, portée simultanément par `wlan0` et `eth0`. Le noyau résout la route vers la passerelle via `wlan0`, et émet donc son ARP pour la passerelle depuis la carte Wi-Fi.

### Correctif retenu

Épingler la route vers la passerelle sur `eth0` :

```sh
ip route replace <LAN-GATEWAY-IP>/32 dev eth0 src <LAN-IP-SERVER> metric 1
```

L'ARP pour la passerelle sort alors par `eth0`, la `<ISP-BOX>` associe correctement `.40` à la MAC filaire, et le trafic est fiable.

Mesures, avec la même boucle de diagnostic (30 tours de `ping` + `curl` vers `1.1.1.1`, un échec = symptôme reproduit) :

| Configuration | Échecs |
|---|---|
| Deux interfaces, sans épinglage | **6 / 10** |
| `eth0` seul (IPv4 de `wlan0` retiré) | 1 / 15 (le premier tour, transitoire) |
| Deux interfaces, épinglage manuel | **0 / 40** |
| Deux interfaces, gardien avec `ip route replace` toutes les 3 s | 4 / 30 |
| Deux interfaces, gardien idempotent | **0 / 30** |

Le `ip route replace` répété supprimait puis recréait la route, créant une micro-coupure. Le gardien ne touche donc à la route que si l'état diffère.

### Repli automatique

Le gardien `/usr/local/bin/uplink-guard` tourne sous `supervise-daemon`, enregistré au runlevel `default`. Sa règle est unique : `eth0` présent (carrier et adresse IPv4) → épingler la passerelle sur `eth0` ; sinon → retirer l'épinglage et laisser `wlan0` reprendre. `wlan0` n'est jamais coupé.

Repli testé le 2026-10-05 :

| Étape | Routes | Résultat |
|---|---|---|
| `ip link set eth0 down` | épinglage retiré, `wlan0` seul (`metric 303`) | 0 % de perte, HTTP 301, via Wi-Fi |
| `ip link set eth0 up` | épinglage restauré, `eth0` (`metric 202`) prioritaire | 0 % de perte, 14,6 ms, HTTP 301 |

La session SSH n'est pas tombée pendant les deux transitions.

### Vérifications

Après correctif, depuis le serveur : 0 échec sur 30 tours, ping `8.8.8.8` à 14,2 / 14,5 / 14,8 ms. Depuis le Mac, sur le tailnet : 15,4 / 19,3 / 24,0 ms, écart-type 2,0 ms, contre 16,7 / 28,2 / **70,5** ms et écart-type 18 ms sur Wi-Fi. Le pic est passé de 70 ms à 24 ms.

Reste à vérifier un redémarrage complet. La configuration est persistante et validée par `ifup -n`, le gardien est au runlevel `default`, et le service `networking` continue la boucle si `eth0` échoue. Le risque est donc faible, mais l'essai n'a pas été fait.

### État final, en service

`/etc/network/interfaces` porte `auto eth0` et `iface eth0 inet dhcp`, après `wlan0`. `eth0` est en `<LAN-IP-SERVER>/24`, `wlan0` en `<LAN-IP-WIFI>/24`. La route par défaut passe par `eth0` (`metric 202`), celle de `wlan0` (`metric 303`) reste en repli, et la passerelle est épinglée sur `eth0`.

| Objet | État |
|---|---|
| `eth0`, adaptateur RTL8156 | en service, 1 Gbit/s |
| `wlan0` | associé, repli automatique |
| `/usr/local/bin/uplink-guard` | en service, supervisé, au runlevel `default` |
| `/etc/init.d/uplink-guard` | en service |
| `ethtool` 7.0 et `ifupdown-ng-ethtool` | installés le 2026-10-05, binaires de diagnostic |
| `/etc/network/interfaces.bak.202610052234` | sauvegarde avant correctif |
| `/etc/network/interfaces.bak.202610052137` | sauvegarde de l'état d'origine |

### Aggravants Wi-Fi non corrigés

Le Wi-Fi reste le repli, et deux défauts subsistent. Les corriger impose une désassociation, donc un risque de perte d'accès sur une machine sans accès physique. À faire seulement avec quelqu'un sur place.

1. `iw reg get` renvoie `country 00: DFS-UNSET`, et **tous** les canaux sont en `PASSIVE-SCAN`. Le domaine réglementaire n'a jamais été posé, défaut connu avec `iwlwifi`. `iw reg set FR` le corrigerait.
2. `wpa_supplicant` tourne sous `supervise-daemon` avec `--respawn-max 5 --respawn-period 1800`. Au-delà de cinq redémarrages en 30 minutes, le superviseur renonce et le serveur n'a plus de repli.

### Fragilité indépendante, côté Mac

Les résolveurs du Mac sont `100.100.100.100` et `fd7a:115c:a1e0::53`, c'est-à-dire MagicDNS. Toute résolution de nom dépend donc du tailnet, donc de ce Wi-Fi instable. Une seconde cause de « ça marche à peu près », distincte de celle du serveur. Le contournement consiste à garder MagicDNS mais à ajouter un résolveur public en second. Rien n'a été modifié.

## Objectif

Un serveur domestique multifonction fait de microservices. Il utilise Alpine et Docker. Il appartient à un tailnet Tailscale.

Le tailnet doit offrir deux sorties. Chaque appareil choisit sa sortie dans l'app Tailscale. Les deux voies sont en service.

## Vocabulaire du projet

Le **serveur** est le laptop `<SERVER-MODEL>` sous Alpine. Docker y empile les conteneurs.

Un **conteneur** est un petit système avec ses propres fichiers. Il est isolé des autres conteneurs.

Un **espace réseau** est une pièce isolée avec sa propre table de routage. Un programme qui y tourne sort par la porte de cette pièce.

Un **exit node** est un nœud qui relaie le trafic des autres appareils vers Internet.

Un **tailnet** est un réseau privé créé par Tailscale. Chaque nœud du tailnet a une adresse qui commence par `100.`.

## État global

- [x] Alpine 3.24 installé sur le laptop `<SERVER-BRAND>`, nom d'hôte `<OLD-SERVER-NAME>`
- [x] SSH durci : clé seule, `PasswordAuthentication no`, connexion root désactivée
- [x] Utilisateur `<ADMIN-ACCOUNT>` et `doas` configurés
- [x] Docker 29.5.x et compose v5.1.4 installés, Docker démarre au boot
- [x] Phase B, voie 1, sortie directe `<OLD-SERVER-NAME>`, construite, testée, identité persistante depuis le 2026-10-03 (cf. « Incident »)
- [x] Phase B, voie 2, sortie anonymisée `<OLD-NODE-EXIT-NYMVPN>`, tunnel Nym établi, nœud Tailscale en ligne, relais validé par `loop.sh` le 2026-10-03
- [ ] Phase C, microservices : AdGuard Home, WoL
- [ ] Phase D, surveillance et notifications : ntfy
- [ ] Repo GitHub privé et README

## Décisions actées

| Domaine | Décision |
|---|---|
| Menace | Le fournisseur d'accès et les métadonnées. Le mode fast de Nym est retenu, car le mixnet est trop lent. Le géo-bypass est désactivé : le client ne doit pas signaler sa localisation au réseau Nym. |
| Sortie pour les appareils | Deux exit nodes Tailscale distincts. L'utilisateur choisit dans l'app de chaque appareil. `<OLD-SERVER-NAME>` sort en direct. `<OLD-NODE-EXIT-NYMVPN>` sort par un anonymiseur. |
| Sortie pour les microservices | Un choix par service. Le `tailscaled` du service pointe vers `<OLD-SERVER-NAME>`, vers `<OLD-NODE-EXIT-NYMVPN>`, ou vers aucun exit node. La bascule ne recrée pas le conteneur. |
| Voie 2 | Objectif confirmé du projet. L'agent choisit l'architecture et la documente. Aucune recette préexistante n'est opposable. |
| Preuve de réussite | L'adresse de sortie vue depuis l'iPhone, avec `<OLD-NODE-EXIT-NYMVPN>` sélectionné, n'est pas celle de la `<ISP-BOX>`. Ce test suffit. |
| Droits de l'agent | Écriture libre sur la voie 2. Aucun droit d'écriture sur la voie 1 sans accord de l'utilisateur. |
| Exposition | Les services restent accessibles par le tailnet seulement. Une exposition publique est une décision séparée et différée. |
| Données | Un disque exportable. La redondance sera décidée quand le disque contiendra des données précieuses. |
| Emplacement des services | Un projet compose par service dans `/opt/<service>`. Le répertoire appartient à root. Chaque projet porte son fichier `.env` de secrets, absent du repo. Le fichier `.env.example` sert de gabarit. Les images Docker sont épinglées par digest. Docker stocke les images et les volumes dans `/var/lib/docker`. |
| Méthode | Le résultat doit être fiable et sûr. L'utilisateur veut comprendre chaque mécanisme avant de continuer. |
| Modalité de travail | L'agent propose et agit. L'utilisateur garde la main sur la voie 1. |
| DNS | AdGuard Home devient un microservice. Son résolveur amont suit le choix de sortie du service. |
| Surveillance | Une alerte signale une coupure de l'anonymiseur ou une coupure de courant. Le service de notification est ntfy. |
| Repo | Le repo GitHub est privé. Il contient les compose, les configurations et ce runbook. |
| Secrets | Les secrets vivent dans `.env`. Le `.gitignore` reste strict. L'agent ne cherche jamais une clé, une graine ou un mot de passe dans les fichiers de l'utilisateur. Il n'utilise un secret que si l'utilisateur le lui donne. |
| PC gaming | Windows sert au jeu. Linux sert de nœud tailnet, de WoL et d'accès distant. |
| Accès au serveur | Le tailnet donne l'accès. Une réservation d'adresse IP sur le réseau local ne servira qu'au jour du WoL. |

## Architecture

```
                          [Internet]
                              │
                    ┌─────────┴─────────┐
                    │   POINT DE CHOIX  │
                    │   <OLD-SERVER-NAME>  ou  <OLD-NODE-EXIT-NYMVPN>
                    └─────────┬─────────┘
              ┌───────────────┴───────────────┐
              │                               │
   ┌──────────▼──────────┐        ┌───────────▼──────────┐
   │  VOIE 1 — DIRECTE   │        │  VOIE 2 — ANONYMISÉE │
   │  <OLD-SERVER-NAME> (tailscale)   │        │  espace réseau dédié  │
   │  network_mode: host │        │  <OLD-NETNS> + nym +   │
   │  sortie <ISP-BOX>        │        │  <OLD-NODE-EXIT-NYMVPN>, Nym fast   │
   │  <WAN-IP-BOX-B>       │        │  sortie anonyme       │
   └─────────────────────┘        └──────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          │                                       │
 ┌────────▼──────────────┐          ┌─────────────▼────────┐
 │  TAILNET Tailscale    │          │  MICROSERVICES       │
 │  iPhone <HOST-IPHONE>      │          │  chaque service a    │
 │  MacBook <HOST-MACBOOK>      │          │  son tailscaled :    │
 │  choix dans l'app :   │          │  --exit-node=<OLD-SERVER-NAME>    │
 │  <OLD-SERVER-NAME>  ou <OLD-NODE-EXIT-NYMVPN>    │          │  --exit-node=<OLD-NODE-EXIT-NYMVPN>│
 └───────────────────────┘          │  --exit-node=none    │
                                    └─────────────────────┘
```

Les deux voies sont parallèles. Elles ne se rejoignent jamais. Le point de choix en amont décrit le rôle des deux nœuds, pas un routeur.

`<OLD-SERVER-NAME>` utilise `network_mode: host`. Il ne partage l'espace réseau d'aucun autre service. Il ne voit aucun tunnel. Le nœud de la voie 2 a sa propre table de routage, ce qui rend le choix possible.

Le tailnet et les microservices sont sur le même niveau. Le tailnet donne accès aux nœuds pour les appareils de l'utilisateur. Les microservices donnent accès à leurs applications.

Un microservice choisit sa sortie avec le paramètre `--exit-node` de son `tailscaled`. Un appareil choisit sa sortie dans l'app Tailscale. Le choix vaut pour la session. Un appareil ne peut pas changer de voie en cours de session.

## Phase B : Tailscale

### Voie 1, `<OLD-SERVER-NAME>`, sortie directe, en service

- [x] Projet compose `/opt/tailscale` créé : image épinglée `tailscale/tailscale@sha256:c507…`, `network_mode: host`, capacités `NET_ADMIN` et `NET_RAW`, `/dev/net/tun`, volume `state`, `restart: unless-stopped`
- [x] Nœud `<OLD-SERVER-NAME>` enregistré, adresse `<TAILNET-IP-EXIT-DIRECT>`. `TS_STATE_DIR=/var/lib/tailscale` depuis le 2026-10-03, pour que l'identité survive à un redémarrage
- [x] Clé d'authentification dans `/opt/tailscale/.env`, mode `600`
- [x] Exit node approuvé dans la console d'administration Tailscale
- [x] Test de bout en bout : depuis l'iPhone, choisissez `<OLD-SERVER-NAME>`, puis ouvrez `https://api.ipify.org`. L'adresse affichée est celle de la `<ISP-BOX>`, `<WAN-IP-BOX-B>` au 2026-10-03

Le tailnet s'appelle Bonnet2B1. Il contient l'iPhone `<HOST-IPHONE>` et le MacBook `<HOST-MACBOOK>`.

### Voie 2, `<OLD-NODE-EXIT-NYMVPN>`, sortie anonymisée, en service

Objectif : un nœud `<OLD-NODE-EXIT-NYMVPN>` du tailnet, approuvé comme exit node, qui fait sortir le trafic par un anonymiseur. L'iPhone le propose alors à côté de `<OLD-SERVER-NAME>` dans l'app tailscale.

Le tunnel Nym fonctionne et sort par une adresse qui change à chaque nouvelle connexion, car les passerelles sont éphémères. Le témoin direct est la `<ISP-BOX>`, l'adresse de sortie de `<OLD-SERVER-NAME>`. Cette adresse est dynamique : elle valait `<WAN-IP-BOX-A>` le 2026-09-30, puis `<WAN-IP-BOX-B>` le 2026-10-03. Mesurez-la au moment du test, ne la supposez pas. Le nœud `<OLD-NODE-EXIT-NYMVPN>` est enregistré dans le tailnet en `<TAILNET-IP-EXIT-NYMVPN>` et approuvé comme exit node.

L'agent a le droit d'écrire sur la voie 2 sans accord préalable. Il n'a aucun droit d'écriture sur la voie 1 (c'est pas exclu mais il faut demander d'abord).

**Les deux voies partagent le même hôte.** Un exit node relaie le trafic des autres appareils. Une route par défaut ou une règle de pare-feu mal placées dans l'espace réseau de la voie 2 peuvent casser la route de l'hôte, et rendre la voie 1 injoignable. Cette raison interdit `network_mode: host` pour la voie 2.

Critères de réussite :

- [x] Le tunnel Nym s'établit et sort par une adresse différente de la `<ISP-BOX>`
- [x] Le port 53 vers l'extérieur est rejeté dans l'espace réseau de la voie 2
- [x] Un nœud `<OLD-NODE-EXIT-NYMVPN>` existe dans le tailnet, avec l'adresse `<TAILNET-IP-EXIT-NYMVPN>`
- [x] Le nœud annonce `0.0.0.0/0` et `::/0`, approuvé comme exit node
- [x] Les règles de routage ont été relevées, sans route de rejet dans la table 52
- [x] La console Tailscale le propose comme exit node, après approbation
- [x] Le nœud est en ligne, `Health` vide, aucun avertissement
- [x] Le trafic d'un appareil, marqué `0x40000`, part en `dev tun0 table 333`
- [x] Le relais est validé par `loop.sh` le 2026-10-03 : l'IP de sortie change, HTTP 200. Le contrôle `<OLD-SERVER-NAME>` est vert, la cible `<OLD-NODE-EXIT-NYMVPN>` est verte
- [x] Depuis l'iPhone, l'app propose `<OLD-NODE-EXIT-NYMVPN>` à côté de `<OLD-SERVER-NAME>`
- [x] Depuis l'iPhone, avec `<OLD-NODE-EXIT-NYMVPN>` sélectionné, `https://api.ipify.org` affiche une adresse différente de la `<ISP-BOX>`
- [ ] La voie 1 répond toujours, avec `<OLD-SERVER-NAME>` sélectionné, la même adresse que la `<ISP-BOX>`

#### Architecture retenue

Un conteneur `<OLD-NETNS>` tient l'espace réseau. Il ne fait rien d'autre que dormir. `nym` et `<OLD-NODE-EXIT-NYMVPN>` le rejoignent avec `network_mode: service:netns`. Les trois partagent donc les mêmes interfaces, les mêmes tables de routage et les mêmes règles nft.

Le conteneur dédié évite un piège : un espace réseau appartient au conteneur qui le crée. Avec `network_mode: service:nym`, un simple redémarrage de `nym` détruirait l'espace, et `tailscaled`, resté accroché à l'ancien, perdrait ses interfaces. L'échec est silencieux côté nym. `<OLD-NETNS>` ne redémarre jamais seul, donc `nym` et `<OLD-NODE-EXIT-NYMVPN>` peuvent être recréés séparément.

```
   espace réseau du conteneur <OLD-NETNS>
   ┌──────────────────────────────────────────────┐
   │  eth0  <DOCKER-INTERNAL-IP>  ──► <ISP-BOX>, <WAN-IP-BOX-B>   │
   │                                              │
   │  tun0  ──► réseau Nym, 2 sauts               │
   │                                              │
   │  tailscale0  ──► les appareils du tailnet    │
   └───────────────┬──────────────────────────────┘
                   │ tout le trafic non marqué
                   ▼
             table 333, dev tun0
```

Le trafic des appareils arrive sur `tailscale0`, n'est pas marqué, et la règle `not from all fwmark 0x14d lookup 333` l'envoie dans la table 333, dont la route par défaut pointe sur `tun0`. Le trafic-marké de Tailscale (`0x80000`) saute cette règle et sort par `eth0`, ce qui évite la boucle.

`<OLD-NODE-EXIT-NYMVPN>` utilise le mode noyau (`TS_USERSPACE=false`). En mode espace utilisateur, Tailscale marque ses paquets avec `0x80000`, mais le client Nym marque aussi ses propres sockets avec `0x14d`. Les deux marques peuvent se confondre et le trafic peut repartir par la table principale. Le mode noyau évite cette ambiguïté.

#### Fichiers du projet

Le projet compose vit dans `/opt/tailscale-nym`, répertoire root, avec le fichier `.env` des secrets. Les sources sont dans `/Users/<LOCAL-USER>/server-config/tailscale-nym`.

| Fichier | Rôle |
|---|---|
| `Dockerfile` | Image Debian bookworm, base et tarball Nym épinglés par digest et SHA-256 |
| `Dockerfile.tailscale` | Image Tailscale dérivée, qui force le backend iptables sur nft |
| `nym-entrypoint.sh` | Dbus, polkit, `nym-vpnd`, puis le superviseur de connexion |
| `49-nymvpn.rules` | Règle polkit qui autorise les actions Nym sur le socket local |
| `docker-compose.yaml` | Les deux services, l'espace réseau partagé, les sysctl |
| `.env` | La clé Tailscale, mode `600`, jamais dans le repo |
| `etc-nym/nym-vpnd.json` | Configuration Nym générée et persistée |

Il n'existe pas d'image Nym officielle pour Linux. L'image est construite localement à partir de Debian bookworm, car le client officiel ne fournit que des paquets macOS. La version `2026.12.4` est la dernière qui livre des binaires Linux. Le tarball est vérifié par SHA-256 avant extraction.

#### Pièges rencontrés

Ces obstacles ont bloqué la mise en service. Chacun a une cause précise et distincte des autres.

**1. `sendmmsg: operation not permitted` à la poignée de main.** Le client Nym pose ses règles nft après avoir démarré WireGuard. La première poignée de main arrive donc avant que les règles ne l'autorisent, tombe sur la règle `reject` finale, et le noyau renvoie un `EPERM` au processus local. C'est le bug amont [6303](https://github.com/nymtech/nym-vpn-client/issues/6303), dont le correctif [6238](https://github.com/nymtech/nym-vpn-client/pull/6238) n'est pas fusionné. Le correctif utilisé est `"netstack": true`. Il remplace l'interface du second saut par une pile réseau en espace utilisateur, ce qui supprime le conflit. Après ce réglage, le compteur d'erreurs `sendmmsg` tombe à zéro.

**2. `Failed to apply src_valid_mark: Read-only file system`.** Nym doit marquer les paquets reçus du tunnel pour que sa propre règle de routage les exclue de la table 333. Docker monte `/proc/sys` en lecture seule, donc l'écriture échoue, et le tunnel ne se monte jamais. Le correctif passe par `sysctls` du compose, sur `net.ipv4.conf.default`. Une interface créée ensuite hérite de ces valeurs, au moment où Nym crée `tun0`. Cette méthode évite d'ajouter la capacité `SYS_ADMIN` au conteneur. Sans ce réglage, la connexion reste bloquée à l'étape `registering with gateways`.

**3. `Disconnected` pris pour un état transitoire.** Dans le premier superviseur, le motif `*Disconnect*` couvrait aussi `Disconnected`. Le superviseur croyait le tunnel en cours de connexion et n'appelait jamais `nym-vpnc connect`. Séparez les états transitoires réels, `Connecting`, `Reconnecting`, `Registering`, `Resolving` et `Unregistering`, de l'état stable `Disconnected`, qui doit déclencher une tentative.

**4. Le nœud Tailscale ne pouvait pas s'enregistrer.** Le symptôme était trompeur, un RST et non un délai. Le plan de contrôle renvoyait `connection refused`, donc un rejet actif, pas un blocage. La cause : `tailscaled` marque son propre trafic avec `0x80000`, et ses règles le routent vers la table principale, donc vers `eth0`. Or la chaîne `output` de Nym est en `policy drop` et n'autorise que `oif "tun0"` et les passerelles de Nym. Tout le reste tombe sur le `reject` final.

Nym n'offre aucun paramètre pour désactiver son pare-feu, vérifié par recherche de chaînes dans le binaire. Deux contournements étaient possibles. Le premier, ajouter une règle `accept` dans la chaîne `output` de Nym, est à écarter : Nym réapplique son pare-feu à chaque connexion et effacerait la règle. Le second, faire entrer le trafic marqué par le tunnel, est retenu.

Nym installe ses règles juste avant celles de Tailscale, et il les décale à chaque connexion. Une priorité fixe ne tient donc pas. Le superviseur lit la priorité réelle de Nym, puis se place deux unités en dessous. Il range la route directe dans une table dédiée, la table 1000 :

```
ip rule add priority <n-1> fwmark 0x80000/0xff0000 lookup 1000
```

Le trafic marqué sort alors par `oif "eth0"`, que la chaîne `output` de Nym accepte. Aucun bistouri sur le pare-feu de Nym. Le superviseur repose la règle à chaque boucle, car Nym reconstruit ses chaînes et ses règles.

Le superviseur pose aussi une règle de retour, deux unités sous Nym :

```
ip rule add priority <n-2> to 100.64.0.0/10 lookup 52
```

Cette règle renvoie vers `tailscale0` la réponse qui arrive du tunnel à destination d'un client. Sans elle, la réponse suit la règle de Nym et repart dans le tunnel.

Conséquence à connaître : le trafic de contrôle de Tailscale, les relais DERP et les échanges WireGuard entre pairs restent en direct par `eth0`, hors du tunnel. C'est nécessaire, le mixnet coupe la connexion longue du plan de contrôle au bout de deux minutes et le nœud passe hors ligne. Seul le trafic relayé des clients passe par Nym. Le fail-closed porte donc sur les clients, pas sur le contrôle.

**5. Le nœud passait hors ligne dès son approbation comme exit node.** Le nœud était enregistré et en ligne, puis l'approbation l'a fait basculer hors ligne. Le symptôme était un `context canceled` sur l'interrogation du plan de contrôle, donc une panne de synchronisation et non une panne réseau, le tunnel étant sain. Deux causes se cumulaient.

La première : `tailscaled` n'arrivait pas à installer ses règles de pare-feu.

```
running [/usr/sbin/iptables -t filter -N ts-input --wait]: exit status 3:
  iptables v1.8.11 (legacy): can't initialize iptables table `filter'
```

L'image Tailscale officielle pointe `/usr/sbin/iptables` vers `iptables-legacy`. Le noyau `6.18.53-0-lts` d'Alpine compile le support iptables en dur et ne fournit aucun module `ip_tables` dans `/lib/modules`. L'iptables legacy ne peut donc jamais fonctionner sur cet hôte. `tailscaled` n'a ni option de ligne de commande ni variable d'environnement pour choisir son backend. La voie 1 n'a jamais eu ce problème parce qu'elle tourne en mode espace utilisateur, qui n'installe aucune règle de pare-feu. Le correctif est l'image dérivée `local/tailscale-nft:1.102.5`, qui repointe les liens symboliques vers `iptables-nft` et `ip6tables-nft`, déjà présents dans l'image.

La seconde : `tailscaled` signalait `Subnet routing is enabled, but IP forwarding is disabled`, alors que `net.ipv4.ip_forward` valait bien 1. La cause est IPv6. Tailscale refuse d'annoncer `0.0.0.0/0` sans `::/0`, donc les deux routes sont toujours publiées, et son contrôle exige alors le forwarding IPv6, qui valait 0. Le correctif ajoute `net.ipv6.conf.all.forwarding` et `net.ipv6.conf.default.forwarding` aux sysctl du compose.

Activer le forwarding IPv6 n'ouvre aucune fuite. Le namespace n'a aucune route IPv6 par défaut, seulement des adresses lien-local et le préfixe unique local du tailnet sur `tailscale0`. Un paquet IPv6 d'un client n'a nulle part où aller, et la chaîne `output` de Nym est en `policy drop`. Le comportement reste fail-closed. Si un jour vous ajoutez une sortie IPv6, ce raisonnement ne vaut plus et il faut rouvrir le dossier.

**6. Le client iOS perdait l'internet par le DNS local.** Le Mac, client de la même voie, résolvait par MagicDNS en IPv4 et sortait normalement. Le téléphone, lui, envoyait ses requêtes DNS au résolveur IPv6 du routeur. Ce résolveur est un préfixe global, donc le téléphone le routait dans le tunnel, et l'exit n'a aucune route IPv6. Les requêtes tombaient dans le vide, sans réponse, et le téléphone perdait toute résolution, donc tout l'internet. Le Mac différait sur un seul point : `scutil --dns` montrait `100.100.100.100` sur `utun8`, alors que le téléphone gardait le DNS du routeur.
La cause est un réglage du client. L'application iOS n'activait pas son option DNS, donc iOS continuait d'utiliser le résolveur appris sur le Wi-Fi. Après activation du DNS Tailscale, iOS utilise MagicDNS, résout en IPv4, et l'internet revient. Contrôle : une capture sur `tailscale0` ne montre plus que des flux IPv4 du client. La même capture, avant le réglage, ne montrait que des requêtes DNS IPv6 vers le routeur, sans réponse.

#### Routage mesuré

Relevé dans l'espace réseau du conteneur, tunnel connecté. Les numéros bougent à chaque connexion, car Nym décale ses règles. L'ordre, lui, ne change pas :

```
0:      from all lookup local
5206:   from all to 100.64.0.0/10 lookup 52
5207:   from all fwmark 0x80000/0xff0000 lookup 1000
5208:   from all lookup main suppress_prefixlength 0
5209:   not from all fwmark 0x14d lookup 333
5210:   from all fwmark 0x80000/0xff0000 lookup main
5230:   from all fwmark 0x80000/0xff0000 lookup default
5250:   from all fwmark 0x80000/0xff0000 unreachable
5270:   from all lookup 52
32766:  from all lookup main
32767:  from all lookup default

table  333 : default dev tun0 proto static mtu 1340
table 1000 : default via <gw> dev eth0
table   52 : les pairs du tailnet, dev tailscale0
```

Quatre blocs se lisent de haut en bas. Le superviseur place la règle de retour, puis sa règle d'accès direct. Nym place ses deux règles. Tailscale place les siennes. Le superviseur lit la position réelle de Nym et se met juste au-dessus, donc l'ordre tient même quand Nym se décale.

La table 52 ne contient que des routes vers les pairs, aucune route de rejet `0.0.0.0/1`. Un client qui demande une adresse publique ne trouve donc rien dans la table 52, et son trafic retombe sur la règle `not from all fwmark 0x14d lookup 333`, donc dans le tunnel. C'est le comportement voulu. Revérifiez-le après chaque mise à jour de Tailscale : une route de rejet dans la table 52 noierait tout le trafic sans message d'erreur.

La règle `to 100.64.0.0/10 lookup 52` renvoie au client la réponse qui arrive du tunnel. Elle passe avant toutes les autres.

La règle `fwmark 0x80000/0xff0000 lookup 1000` envoie le trafic propre de Tailscale par `eth0`, hors du tunnel. Sans elle, Nym capturerait ce trafic et le ferait passer par le mixnet, qui coupe la connexion de contrôle au bout de deux minutes.

La règle `not from all fwmark 0x14d lookup 333` appartient à Nym. Elle envoie dans la table 333 tout le trafic qui ne porte pas la marque de Nym.

La règle `from all lookup main suppress_prefixlength 0` masque la route par défaut de la table principale. Le trafic non marqué ne peut donc pas atteindre `eth0` par la route par défaut. Si le tunnel tombe, le trafic est perdu au lieu de repartir en direct. C'est le comportement fail-closed voulu. Vérifiez-le avec `ip route get 8.8.8.8` dans le conteneur, la réponse doit mentionner `tun0` et la table 333.

`tailscaled` utilise deux marques distinctes et il faut les connaître pour raisonner. Son propre trafic porte `0x80000` : contrôle, DERP et échanges WireGuard entre pairs. La règle du superviseur l'envoie en direct par `eth0`. Le trafic **relayé** des clients porte `0x40000`. Cette marque ne correspond pas au masque `0xff0000`, donc le trafic des clients échappe à la règle du superviseur et suit le chemin normal : la règle 5270 ne trouve rien dans la table 52 pour une adresse publique, puis la règle de Nym l'envoie dans la table 333. Vérifiez-le après toute mise à jour de Tailscale avec `ip route get 9.9.9.9 from <TAILNET-IP-EXIT-NYMVPN> mark 0x40000`, la réponse doit mentionner `tun0` et la table 333.

#### Pare-feu Nym

Nym installe une table `inet nym` avec `policy drop` sur les chaînes `input`, `output` et `forward`. Les chaînes `output` et `forward` rejettent le port 53 :

```
chain output  { policy drop; udp dport 53 reject; tcp dport 53 reject with tcp reset; reject; }
chain forward { policy drop; udp dport 53 reject; tcp dport 53 reject with tcp reset; reject; }
```

Le résolveur interne de Nym répond. Le port 53 vers l'extérieur est refusé par le noyau, ce qui renvoie une erreur à l'appelant. N'attendez pas d'absence de réponse, elle signifierait un blocage silencieux.

La table porte aussi une chaîne `nat`, accrochée à `postrouting`, et elle reste vide. Le relais n'a pas besoin de masquerade : la passerelle de sortie Nym NAT le trafic, et la règle de retour `to 100.64.0.0/10 lookup 52` ramène la réponse vers `tailscale0`. Une version antérieure du superviseur écrivait dans `postrouting`, une chaîne qui n'existe pas. L'écriture échouait en silence et le journal annonçait un succès. Ce bloc a été retiré le 2026-10-03.

Au démarrage, Nym tente de réécrire `src_valid_mark` et `arp_ignore` dans `/proc/sys`. Le système de fichiers est en lecture seule, donc il journalise `Failed to apply ...: Read-only file system`. Les valeurs sont déjà posées par les `sysctls` du service `netns`. Ces erreurs sont bénignes, ne les traitez pas comme une panne.

#### Superviseur de connexion

`nym-vpnd` ne rétablit pas le tunnel tout seul après un redémarrage. Le superviseur, dans l'entrypoint, garde la connexion. Il lance `nym-vpnd` en arrière-plan, puis boucle toutes les 30 secondes. Il appelle `nym-vpnc connect` tant que l'état n'est pas `Connected`, et attend pendant les états transitoires. Il n'abandonne jamais. Il relaie `SIGTERM` et `SIGINT` vers `nym-vpnd` pour que l'arrêt du conteneur reste propre.

Ce choix a été validé par un test : après un `nym-vpnc disconnect` manuel, le superviseur a rétabli le tunnel en moins de 12 secondes, avec les mêmes passerelles.

Le service `<OLD-NODE-EXIT-NYMVPN>` démarre quoi qu'il arrive. Si le tunnel Nym manque, `<OLD-NODE-EXIT-NYMVPN>` est annoncé sans route par défaut, donc le trafic est perdu au lieu de fuir.

#### Commandes de mise en place

Sur `<OLD-SERVER-NAME>`, avec `doas` :

```
cd /opt/tailscale-nym
docker compose build nym
docker compose up -d --no-deps nym
```

Après un rebuild, ne lancez pas `docker compose up -d` sans argument. Compose recréerait `<OLD-NETNS>`, dont l'image est partagée avec `nym`, et l'espace réseau serait perdu. `--no-deps` ne recrée que `nym`. Si la pile est arrêtée, lancez `docker compose up -d` une fois, puis relisez l'identifiant de l'espace : `docker inspect -f '{{.NetworkSettings.SandboxKey}}' <OLD-NETNS>`.

Pour l'état :

```
docker exec nym nym-vpnc status --table-style blank
docker exec nym sh -c 'curl -s --max-time 20 https://api.ipify.org; echo'
docker exec nym ip rule
docker exec nym ip route show table 333
docker logs nym | grep superviseur
```

Ne lancez jamais `nym-vpnd -v`. Le daemon écrit la mnemonic Nym dans ses journaux au niveau `info`. La mnemonic vit dans le volume `nym-data`, au chemin `/var/lib/nym-vpnd/mainnet/mnemonic.json` dans le conteneur. Ne la copiez jamais sur le disque de l'hôte.

#### Redémarrage de l'hôte

Testé le 2026-10-03. Un `doas reboot` de l'hôte est sans effet sur les deux voies. Au retour, les quatre conteneurs remontent seuls, car tous portent `restart: unless-stopped`. `<OLD-SERVER-NAME>` reprend `<TAILNET-IP-EXIT-DIRECT>` et `<OLD-NODE-EXIT-NYMVPN>` reprend `<TAILNET-IP-EXIT-NYMVPN>`, car leur identité vit dans un volume. Le tunnel Nym se reconnecte seul, en une tentative. L'espace réseau `<OLD-NETNS>` est recréé, avec un identifiant neuf.

Après le reboot, attendez une minute, puis vérifiez :

```sh
doas docker ps -a --format '{{.Names}} {{.Status}}'
doas docker exec <OLD-NODE-EXIT-NYMVPN> tailscale ip -4
doas docker logs nym | grep -E 'New tunnel state|superviseur'
```

#### Reste à faire

- Tester depuis l'iPhone avec `<OLD-NODE-EXIT-NYMVPN>` sélectionné, puis vérifier que la voie 1 répond toujours
- Mesurer la MTU effective sur du trafic réel, le bug [6465](https://github.com/nymtech/nym-vpn-client/issues/6465) visant les tunnels Nym au-dessus de 1300
- Révoquer les clés d'authentification Tailscale dans la console

### Étapes communes

- [x] Testez un reboot distant. Le serveur redémarre seul, Docker relance `<OLD-SERVER-NAME>` et `<OLD-NODE-EXIT-NYMVPN>`, les deux nœuds reviennent en ligne
- [ ] Durcissez SSH. Le service écoute encore sur `0.0.0.0:22`. Restreignez l'écoute au tailnet après le test d'accès distant
- [ ] Décidez du réglage `--accept-dns` le jour de la tâche AdGuard Home

## Phase C : microservices

Chaque service suit le même gabarit. Un `tailscaled` en conteneur compagnon donne au service une adresse Tailscale. Le service pointe ensuite vers `<OLD-SERVER-NAME>` pour un accès direct, vers `<OLD-NODE-EXIT-NYMVPN>` pour un accès anonymisé, ou vers `none` pour un accès sans exit node.

Démarrez le `tailscaled` avec `--accept-routes=true`. Sans ce drapeau, le nœud ignore la route de l'exit node, et la bascule reste sans effet.

Pointer le résolveur DNS du service vers `100.100.100.100`. Sinon les requêtes de noms de domaine partent vers la `<ISP-BOX>` et quittent le tailnet.

Épinglez l'image par digest. Ajoutez `restart: unless-stopped`. Placez le projet dans `/opt/<service>`, avec le répertoire appartenant à root.

Pour changer la sortie d'un service en cours d'exécution, exécutez une de ces trois commandes :

```sh
doas docker exec <service> tailscale set --exit-node=<OLD-NODE-EXIT-NYMVPN>   # anonymisé
doas docker exec <service> tailscale set --exit-node=<OLD-SERVER-NAME>       # direct, plein débit
doas docker exec <service> tailscale set --exit-node=none       # pas d'exit node
```

Relisez la sortie active avec `tailscale status`. La console Tailscale affiche aussi la sortie de chaque nœud. Vous pouvez créer un alias court pour chaque service.

## Archive : mesures de l'essai précédent, 2026-09-29

Ces mesures viennent de l'essai de la voie 2, avec l'architecture qui a échoué, et d'un tunnel Nym. **Elles peuvent être fausses pour une autre architecture, et certaines peuvent venir de cette architecture elle-même plutôt que du fournisseur d'anonymisation.** Utilisez-les comme des pistes, jamais comme des propriétés établies. Revalidez chaque chiffre avant de vous y fier.

| Mesure | Résultat observé |
|---|---|
| Sortie TCP par l'espace réseau Nym | `141.227.149.187`, anonymisé |
| Témoin hors tunnel | `<WAN-IP-BOX-A>`, direct |
| ICMP par l'espace réseau Nym | 2 réponses sur 2, 52 ms, 0 % de perte |
| DNS en UDP vers 1.1.1.1 par le tunnel | `Operation not permitted`, puis délai dépassé |
| DNS témoin hors tunnel | 4 adresses reçues |
| MTU du tunnel Nym | 1340 octets |
| Pare-feu de l'espace réseau Nym | chaîne `output` en `policy drop` |

Faits utiles, indépendants de l'architecture essayée :

- La version par défaut du compose Nym, `2026.11.3`, n'existe plus dans le PPA. La version qui fonctionnait était `2026.12.4`.
- L'erreur `InvalidEntryGatewayIdentity` du client Nym se contourne en sélectionnant un pays, via `ENTRY_GATEWAY_COUNTRY` et `EXIT_GATEWAY_COUNTRY`.
- Le client Nym échoue parfois au handshake avec `sendmmsg: operation not permitted`. Le paramètre `"netstack": true` dans sa configuration corrige ce symptôme. L'issue `https://github.com/nymtech/nym-vpn-client/issues/3658` rapporte la même erreur, fermée sans correctif. Confirmé le 2026-09-30, et la cause réelle est plus précise. Voir « Pièges rencontrés » dans la voie 2, avec l'issue [6303](https://github.com/nymtech/nym-vpn-client/issues/6303).
- Le client Nym peut écrire ses propres règles `nft` dans son espace réseau. Un exit node qui partage cet espace doit en tenir compte, sinon son trafic est détruit à l'envoi, avant même de sortir.
- Le tunnel Nym s'est arrêté de lui-même le 2026-09-28 alors que ses conteneurs se déclaraient `healthy`. Surveillez l'état réel du tunnel, pas l'état de santé des conteneurs.
- Une exception pare-feu ajoutée à la main dans l'espace réseau ne survit pas au redémarrage du conteneur qui l'a créée. Tout correctif en mémoire demande une réinjection, donc une dépendance à l'ordre de démarrage. C'est une source d'instabilité, traitez-la comme un défaut, pas comme une étape.

## Mode de travail

L'agent propose les commandes et les exécute. L'utilisateur colle les sorties, ou l'agent les lit lui-même quand il a l'accès.

Connexion au serveur, par le tailnet :

```sh
ssh <ADMIN-ACCOUNT>@<TAILNET-IP-EXIT-DIRECT>
```

L'adresse `<LAN-IP-WIFI>` est l'adresse du réseau local et fonctionne depuis une machine sur place. Depuis un Mac connecté au tailnet, elle échoue : le trafic est routé par erreur dans un tunnel local. Préférez l'adresse du tailnet.

L'utilisateur saisit son mot de passe `doas`. L'agent ne doit pas chercher de clé, de graine ou de mot de passe dans les fichiers de l'utilisateur. Il n'utilise un secret que si l'utilisateur le lui donne.

Une ancienne session web utilisait `ttyd` et `tmux` sur le port 7681. L'utilisateur a demandé sa suppression le 2026-09-28, pour garder Alpine minimal et pour des raisons de sécurité. La suppression a retiré `ttyd`, `tmux` et le cache des paquets.

## Glossaire

**Espace réseau** : pièce isolée avec sa propre table de routage. `network_mode: service:X` place un conteneur dans celle de X. Un conteneur qui la partage sort par la même porte.

**Table de routage** : liste qui associe chaque destination à une porte. Une entrée `default dev tun0` envoie tout le trafic non étiqueté dans un tunnel.

**Étiquette de paquet** (`fwmark`) : marque appliquée à un paquet. Un anonymiseur peut étiqueter son propre trafic pour qu'il n'entre pas dans son tunnel.

**Route par défaut** : règle de secours. Elle envoie tout le trafic non prévu vers une seule porte. Une route par défaut pointée sur un tunnel coupe toute fuite.

**Exit node** : nœud du tailnet qui offre une sortie Internet. La sortie de `<OLD-SERVER-NAME>` passe par la `<ISP-BOX>`. La sortie de `<OLD-NODE-EXIT-NYMVPN>` passe par Nym en mode fast.

**Conteneur compagnon** (*sidecar*) : conteneur qui fournit un service à un autre conteneur. Ici, `tailscaled` accompagne l'application.

**`--accept-routes=true`** : autorise un nœud à suivre la route d'un exit node. Sans ce drapeau, la bascule reste sans effet.

**DERP** : relais de secours de Tailscale. Il utilise HTTPS sur le port 443. Tailscale l'emploie quand la connexion directe entre deux nœuds est bloquée.

**MTU** : taille maximale d'un paquet. Deux tunnels empilés imposent une valeur plus petite que celle du tunnel extérieur.

**Anonymiseur** : service qui relaie le trafic vers Internet en cachant l'adresse d'origine. L'anonymiseur de la voie 2 est Nym, en mode fast.

**SOCKS5** : proxy par application. Ce protocole transporte TCP seulement, sans UDP. Un exit node ne l'utilise pas.

**Mode fast** : trajet en deux sauts, une passerelle d'entrée puis une passerelle de sortie. L'adresse de sortie visible change selon la passerelle sélectionnée.

**`.env`** : fichier de secrets lu par compose. Le fichier reste absent du repo. Le fichier `.env.example` sert de gabarit.

**Full-tunnel** : configuration où tout le trafic non étiqueté passe par le tunnel.

## Maintenance

Mettez à jour le système volontairement. N'utilisez jamais l'image `latest` sans contrôle.

Pour Alpine et Docker, mettez à jour chaque trimestre et après un correctif de sécurité important :

```sh
doas apk update && doas apk upgrade
```

Redémarrez le serveur si le noyau a changé. Le module `tun` se recharge au boot, et Docker redémarre avec lui.

Pour `<OLD-SERVER-NAME>`, changez l'image par digest. Exécutez `docker compose pull`, puis `up -d --force-recreate`, dans `/opt/tailscale`. L'état du nœud reste dans le volume `state`.

Pour `<OLD-NODE-EXIT-NYMVPN>`, l'image Nym est construite localement. Après une modification des sources, exécutez `docker compose build nym`, puis `docker compose up -d --no-deps nym`, dans `/opt/tailscale-nym`. Ne recréez pas `<OLD-NETNS>` sans recréer aussi `nym` et `<OLD-NODE-EXIT-NYMVPN>`, car l'espace réseau appartient à `<OLD-NETNS>`.

Les clients du tailnet se mettent à jour depuis l'App Store ou le magasin d'applications. Aucune action n'est nécessaire sur le serveur.

N'écrivez pas de script unique avant d'avoir assez de projets. Un script demande lui-même de la maintenance.

## Nettoyage

Cette section existe parce qu'une session de travail peut perdre la mémoire. Tout ce qui suit doit pouvoir être fait par quelqu'un qui n'a rien vécu, à partir de ce runbook seul.

### Ce qui a été installé pour le diagnostic de la voie 2

Sur le Mac, Colima et Docker servent de client Tailscale de test, sans toucher au Mac lui-même. Pour les retirer :

```sh
docker rm -f ts-client
colima stop
brew uninstall colima docker lima
colima delete          # supprime la machine virtuelle et ses volumes
```

Le conteneur de test `ts-client` utilise l'image `tailscale/tailscale:stable`. Depuis le 2026-10-03, cette image est basée sur Alpine 3.22.6 et ne contient ni `curl` ni `dig`. `loop.sh` en a besoin. Depuis la même date, `loop.sh` les installe lui-même : il vérifie la présence du conteneur `ts-client`, puis lance `apk add --no-cache curl bind-tools` si les deux outils manquent. Si cette installation automatique échoue, gardez la commande manuelle :

```sh
docker exec ts-client apk add --no-cache curl bind-tools
```

Le nœud `ts-test` du tailnet se supprime depuis la console Tailscale. Une clé `ephemeral` le ferait disparaître seul. Celle du 2026-10-03 n'était pas éphémère : le nœud s'appelle `ts-test-1`, car `ts-test` existait déjà.

Les deux règles nft temporaires commentées `TEMPO` ont disparu avec les recréations du conteneur `nym`. Vérifiez qu'il n'en reste aucune :

```sh
doas docker exec nym nft list chain inet nym forward
```

### Clés d'authentification à révoquer

Ces clés ont servi au diagnostic ou à l'enregistrement et ne servent plus. Révoquez-les dans la console Tailscale, section des clés.

- La clé de `/opt/tailscale/.env`, consommée le 2026-10-03. Une clé est à usage unique. L'identité du nœud vit maintenant dans le volume `state`, donc la clé n'est plus nécessaire. Elle a été retirée du fichier `.env` et de `docker-compose.yaml` le 2026-10-03.
- La clé de `/opt/tailscale-nym/.env`, utilisée pour `<OLD-NODE-EXIT-NYMVPN>`.
- La clé du conteneur de test `ts-client` sur le Mac, celle qui a créé `ts-test-1`.
- Les clés plus anciennes visibles dans l'historique du shell, `/home/<ADMIN-ACCOUNT>/.ash_history`, notamment celles des lignes 58 et 263.

Le secret `TS_AUTHKEY` de la voie 2 apparaît en clair dans `docker inspect <OLD-NODE-EXIT-NYMVPN>`. C'est normal, la variable est passée par l'environnement du conteneur. Le conteneur `tailscale` de la voie 1 ne porte plus de clé depuis le 2026-10-03. Les fichiers `.env` restent en mode `600`.

### État connu au moment de l'écriture

Les deux voies fonctionnent au 2026-10-03. La voie 1 est en ligne en `<TAILNET-IP-EXIT-DIRECT>`, identité persistante. La voie 2 est en ligne en `<TAILNET-IP-EXIT-NYMVPN>`, tunnel Nym connecté. `loop.sh` rend la cible `<OLD-NODE-EXIT-NYMVPN>` verte. Le test depuis l'iPhone est validé le 2026-10-03, après activation du DNS Tailscale dans l'application iOS. Sans ce réglage, iOS garde le résolveur IPv6 du routeur, que l'exit en fail-closed jette.

## Différé et conditionnel

Le débit réel de la voie 2 reste inconnu. Une mesure contre un fichier de test donnerait le plafond réel. Cette mesure est utile pour classer les services par débit. Elle ne bloque aucune étape.

Le réglage `--accept-dns` reste à `false`, car c'est le défaut du conteneur. Décidez de MagicDNS le jour de la tâche AdGuard Home. Chaque service anonymisé pointera son résolveur vers `100.100.100.100`.

L'exposition publique des services demande un reverse-proxy et un domaine. Faites-la quand le besoin réel arrive.

La redondance du disque et la sauvegarde attendent le moment où le serveur héberge une donnée précieuse.

L'onduleur et la réservation d'adresse IP sur le réseau local attendent le jour du WoL.

La batterie est gonflée et le châssis est déformé. Débranchez la nappe de la batterie. C'est une mesure de sécurité, à planifier sans urgence.

Le nettoyage des images Docker inutilisées reste facultatif.
