# Logbook : les événements passés

Ce fichier raconte ce qui s'est passé sur le serveur. Il contient les incidents, les diagnostics et les pièges. L'état actuel de la machine est dans [architecture.md](architecture.md). Les tâches restantes sont dans [todo.md](todo.md).

## Le retrait de ttyd et de tmux, 2026-09-28

Une ancienne session web utilisait `ttyd` et `tmux` sur le port 7681. L'utilisateur a demandé sa suppression le 2026-09-28, pour garder Alpine minimal et pour des raisons de sécurité. La suppression a retiré `ttyd`, `tmux` et le cache des paquets.

## L'archive : les mesures de l'essai du 2026-09-29

Ces mesures viennent de l'essai de la voie 2, avec l'architecture qui a échoué, et d'un tunnel Nym. Elles peuvent être fausses pour une autre architecture. Certaines peuvent venir de cette architecture plutôt que du fournisseur d'anonymisation. Ces mesures ne sont donc que des pistes. Elles ne font pas foi.

Le projet NymVPN a été retiré le 2026-09-29. Son répertoire `/opt/nymvpn` n'existe plus.

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
- Le client Nym échoue parfois au handshake avec `sendmmsg: operation not permitted`. Le paramètre `"netstack": true` dans sa configuration corrige ce symptôme. L'issue [3658](https://github.com/nymtech/nym-vpn-client/issues/3658) rapporte la même erreur. Elle est fermée sans correctif. Le symptôme est confirmé le 2026-09-30. La cause réelle est plus précise : voir le piège 1, estimé au 2026-09-30, avec l'issue [6303](https://github.com/nymtech/nym-vpn-client/issues/6303).
- Le client Nym peut écrire ses propres règles `nft` dans son espace réseau. Un exit node qui partage cet espace doit en tenir compte. Sinon, son trafic est détruit à l'envoi, avant même de sortir.
- Le tunnel Nym s'est arrêté de lui-même le 2026-09-28 alors que ses conteneurs se déclaraient `healthy`. L'état de santé des conteneurs ne reflète pas l'état réel du tunnel.
- Une exception pare-feu ajoutée à la main dans l'espace réseau ne survit pas au redémarrage du conteneur qui l'a créée. Tout correctif en mémoire demande une réinjection. Il crée donc une dépendance à l'ordre de démarrage. C'est une source d'instabilité. Cette dépendance est un défaut, pas une étape.

## Les pièges de la voie 2, estimés au 2026-09-30

Deux pièges sont insérés à une date estimée. Cette estimation a été faite le 2026-10-08. La date de constat exacte de ces deux pièges n'est pas consignée dans les sources.

##### Piège 1 : sendmmsg: operation not permitted à la poignée de main

Le client Nym pose ses règles nft après avoir démarré WireGuard. La première poignée de main arrive donc avant que les règles ne l'autorisent. Elle tombe sur la règle `reject` finale. Le noyau renvoie un `EPERM` au processus local. C'est le bug amont [6303](https://github.com/nymtech/nym-vpn-client/issues/6303), dont le correctif [6238](https://github.com/nymtech/nym-vpn-client/pull/6238) n'est pas fusionné. Le correctif utilisé est `"netstack": true`. Il remplace l'interface du second saut par une pile réseau en espace utilisateur, ce qui supprime le conflit. Après ce réglage, le compteur d'erreurs `sendmmsg` tombe à zéro.

La date estimée, le 2026-09-30, repose sur le symptôme confirmé ce jour-là, comme le note l'archive du 2026-09-29.

##### Piège 5 : le nœud passait hors ligne dès son approbation comme exit node

Le nœud était enregistré et en ligne. L'approbation comme exit node l'a fait basculer hors ligne. Le symptôme était un `context canceled` sur l'interrogation du plan de contrôle. C'est une panne de synchronisation, pas une panne réseau, le tunnel étant sain. Deux causes se cumulaient.

La première : `tailscaled` n'arrivait pas à installer ses règles de pare-feu.

```
running [/usr/sbin/iptables -t filter -N ts-input --wait]: exit status 3:
  iptables v1.8.11 (legacy): can't initialize iptables table `filter'
```

L'image Tailscale officielle pointe `/usr/sbin/iptables` vers `iptables-legacy`. Le noyau `6.18.53-0-lts` d'Alpine compile le support iptables en dur. Il ne fournit aucun module `ip_tables` dans `/lib/modules`. L'iptables legacy ne peut donc jamais fonctionner sur cet hôte. `tailscaled` n'a ni option de ligne de commande ni variable d'environnement pour choisir son backend. La voie 1 n'a jamais eu ce problème parce qu'elle tourne en mode espace utilisateur. Le mode espace utilisateur n'installe aucune règle de pare-feu. Le correctif est l'image dérivée `local/tailscale-nft:1.102.5`. Elle repointe les liens symboliques vers `iptables-nft` et `ip6tables-nft`, déjà présents dans l'image.

La seconde : `tailscaled` signalait `Subnet routing is enabled, but IP forwarding is disabled`, alors que `net.ipv4.ip_forward` valait bien 1. La cause est IPv6. Tailscale refuse d'annoncer `0.0.0.0/0` sans `::/0`. Les deux routes sont donc toujours publiées. Son contrôle exige alors le forwarding IPv6, qui valait 0. Le correctif ajoute `net.ipv6.conf.all.forwarding` et `net.ipv6.conf.default.forwarding` aux sysctl du compose.

Activer le forwarding IPv6 n'ouvre aucune fuite. Le namespace n'a aucune route IPv6 par défaut. Il n'a que des adresses lien-local et le préfixe unique local du tailnet sur `tailscale0`. Un paquet IPv6 d'un client n'a nulle part où aller. La chaîne `output` de Nym est en `policy drop`. Le comportement reste fail-closed. Ce raisonnement cesse de valoir si une sortie IPv6 est ajoutée un jour.

La date estimée, le 2026-09-30, repose sur la création de l'image `local/tailscale-nft:1.102.5`, relevée sur le serveur le 2026-10-08. Cette image porte le 2026-09-30 à 20:31.

## L'incident du 2026-10-01 : la perte de l'accès à la voie 1

L'agent a détruit l'accès au serveur. Pendant le nettoyage de la voie 2, il a lancé une commande trop large :

```sh
docker ps -a --format "{{.Names}}" | grep -Ei "nym|netns|tailscale" | while read n; do docker rm -f "$n"; done
```

Le motif `tailscale` a matché le conteneur de la voie 1, `tailscale`, dans `/opt/tailscale`, et l'a supprimé. Ce conteneur était la seule voie d'accès. L'utilisateur travaillait par le tailnet et n'avait aucun accès sur place. Le reboot n'a pas rétabli le nœud.

État au 2026-10-01 :

- Le conteneur de la voie 1 a été recréé avec `docker compose up -d` et il tourne.
- L'hôte a été redémarré.
- `<OLD-SERVER-NAME>` n'apparaît toujours pas dans le tailnet.
- La cause exacte est inconnue. Aucun journal n'a pu être lu pendant l'incident, faute de retour console. La suppression du conteneur est le déclencheur.

Piste écartée le 2026-10-03 : une perte de route ou de DNS de l'hôte, avec un `/etc/resolv.conf` pointant vers `100.100.100.100`. Cette adresse est servie par `tailscaled` lui-même. L'hôte répondait normalement. La vraie cause est décrite dans « La résolution du 2026-10-03 ».

Voici ce qui a été fait pour reprendre l'accès, avec un accès physique ou distant.

La commande `docker ps -a` a donné l'état réel du conteneur. Le conteneur de la voie 1 tournait, mais `<OLD-SERVER-NAME>` n'apparaissait pas dans le tailnet.

Pendant l'incident, aucun journal n'a pu être lu, faute de retour console. Le diagnostic du 2026-10-03 a relu les journaux du projet avec `cd /opt/tailscale && docker compose logs --tail 80`. Les motifs cherchés étaient `NeedsLogin`, `network is unreachable`, `no such host` et `panic`.

La route et le DNS de l'hôte ont été relevés avec `ip -4 route`, `cat /etc/resolv.conf` et `ping -c2 1.1.1.1`.

Le conteneur a été recréé et tournait au retour. Le nœud `<OLD-SERVER-NAME>` n'a repris sa place dans le tailnet qu'après le correctif du 2026-10-03.

Leçon : la voie 1 et la voie 2 vivent sur le même hôte. Un motif de nom commun frappe les deux. La règle qui en découle est dans [guidelines.md](guidelines.md), section « Le codage et la configuration ».

### La résolution du 2026-10-03

L'accès distant est revenu par le réseau local. Le diagnostic a montré trois causes côté voie 1.

1. Le compose de la voie 1 montait le volume `state`, mais ne posait pas `TS_STATE_DIR`. `containerboot` démarrait donc avec `--state=mem:`. L'identité du nœud vivait en mémoire. Chaque recréation du conteneur perdait l'identité.
2. Aucune clé d'authentification ne restait pour reconstruire l'identité.
3. `containerboot` donne 60 secondes à `tailscale up`. Sans clé, l'enregistrement attend une validation par URL. Le délai expire. `containerboot` arrête `tailscaled`. Le conteneur sort avec le code 0. `restart: unless-stopped` le relance. Chaque cycle produit une nouvelle URL. La boucle interdit toute connexion par URL.

Le diagnostic a relevé une seconde cause, côté voie 2 : le superviseur écrivait sa règle de masquerade dans `inet nym postrouting`. Cette chaîne n'existe pas. L'écriture échouait en silence et le journal annonçait un faux succès toutes les 30 secondes. Le bloc a été retiré le 2026-10-03. Voir « Le pare-feu Nym » de [architecture.md](architecture.md) pour le détail.

Le correctif au compose pose `TS_STATE_DIR=/var/lib/tailscale` et `TS_AUTHKEY=${TS_AUTHKEY}`. La première variable rend l'identité persistante. La seconde enregistre le nœud immédiatement. La clé vit dans `/opt/tailscale/.env`, en mode `600`.

Après le correctif, `tailscaled.state` apparaît dans le volume. Un `docker restart tailscale` laisse le nœud en ligne, avec la même adresse. Le journal affiche `machineAuthorized=true; authURL=false`.

L'ancien nœud `<OLD-SERVER-NAME>` a été supprimé dans la console. Le nouveau nœud a repris le nom `<OLD-SERVER-NAME>` et l'adresse `<TAILNET-IP-EXIT-DIRECT>`. L'ancienne adresse `<TAILNET-IP-OLD-IDENTITY>` ne sert plus.

## Les pièges de la voie 2, estimés au 2026-10-03

Quatre pièges sont insérés à une date estimée. Cette estimation a été faite le 2026-10-08. Elle repose sur des indices relevés sur le serveur. L'image Nym a été reconstruite le 2026-10-03 à 22:36. Les conteneurs `<OLD-NETNS>` et `<OLD-NODE-EXIT-NYMVPN>` ont été recréés à 22:20. La date de constat exacte de ces quatre pièges n'est pas consignée.

##### Piège 2 : Failed to apply src_valid_mark: Read-only file system

Nym doit marquer les paquets reçus du tunnel pour que sa propre règle de routage les exclue de la table 333. Docker monte `/proc/sys` en lecture seule, donc l'écriture échoue, et le tunnel ne se monte jamais. Le correctif passe par `sysctls` du compose, sur `net.ipv4.conf.default`. Une interface créée ensuite hérite de ces valeurs, au moment où Nym crée `tun0`. Cette méthode évite d'ajouter la capacité `SYS_ADMIN` au conteneur. Sans ce réglage, la connexion reste bloquée à l'étape `registering with gateways`.

##### Piège 3 : Disconnected pris pour un état transitoire

Dans le premier superviseur, le motif `*Disconnect*` couvrait aussi `Disconnected`. Le superviseur croyait le tunnel en cours de connexion. Il n'appelait jamais `nym-vpnc connect`. Le correctif sépare les états transitoires réels, `Connecting`, `Reconnecting`, `Registering`, `Resolving` et `Unregistering`, de l'état stable `Disconnected`. L'état stable déclenche alors une tentative.

##### Piège 4 : le nœud Tailscale ne pouvait pas s'enregistrer

Le symptôme était trompeur, un RST et non un délai. Le plan de contrôle renvoyait `connection refused`, donc un rejet actif, pas un blocage. La cause : `tailscaled` marque son propre trafic avec `0x80000`. Ses règles le routent vers la table principale, donc vers `eth0`. Or la chaîne `output` de Nym est en `policy drop`. Elle n'autorise que `oif "tun0"` et les passerelles de Nym. Tout le reste tombe sur le `reject` final.

Nym n'offre aucun paramètre pour désactiver son pare-feu. La recherche de chaînes dans le binaire l'a confirmé. Deux contournements étaient possibles. Le premier, ajouter une règle `accept` dans la chaîne `output` de Nym, est à écarter. Nym réapplique son pare-feu à chaque connexion et effacerait la règle. Le second, faire entrer le trafic marqué par le tunnel, est retenu.

L'arrangement des règles `ip rule` qui applique ce contournement est décrit dans « Le routage » de [architecture.md](architecture.md).

##### Piège 6 : le client iOS perdait l'internet par le DNS local

Ce piège est daté, pas estimé. Le réglage du client iOS a été validé le 2026-10-03, comme le décrit « Le réglage DNS de l'application iOS ».

Le Mac, client de la même voie, résolvait par MagicDNS en IPv4. Il sortait normalement. Le téléphone, lui, envoyait ses requêtes DNS au résolveur IPv6 du routeur. Ce résolveur est un préfixe global. Le téléphone le routait donc dans le tunnel. L'exit n'a aucune route IPv6. Les requêtes tombaient dans le vide, sans réponse. Le téléphone perdait toute résolution, donc tout l'internet. Le Mac différait sur un seul point : `scutil --dns` montrait `100.100.100.100` sur `utun8`, alors que le téléphone gardait le DNS du routeur.

La cause est un réglage du client. L'application iOS n'activait pas son option DNS. iOS continuait donc d'utiliser le résolveur appris sur le Wi-Fi. Après activation du DNS Tailscale, iOS utilise MagicDNS, résout en IPv4, et l'internet revient. Contrôle : une capture sur `tailscale0` ne montre plus que des flux IPv4 du client. Avant le réglage, la même capture ne montrait que des requêtes DNS IPv6 vers le routeur, sans réponse.

## La validation des deux voies, 2026-10-03

Les deux voies ont été validées le 2026-10-03. La liste ci-dessous donne les critères de réussite, relevés ce jour-là. Le dernier critère a été vérifié le 2026-10-08.

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
- [x] La voie 1 répond toujours, avec `<OLD-SERVER-NAME>` sélectionné, la même adresse que la `<ISP-BOX>`

### Les tâches terminées le 2026-10-08

L'utilisateur a confirmé ce jour-là la fin de trois tâches de [todo.md](todo.md). Elles ont été retirées de ce fichier.

La voie 1 a été testée après un passage par la voie 2. Elle répond avec `<OLD-SERVER-NAME>` sélectionné, avec l'adresse de la `<ISP-BOX>`. La MTU effective de la voie 2 a été mesurée sur du trafic réel le 2026-10-08. Elle vaut 1340 octets. Un paquet de 1340 octets passe, un de 1344 échoue.

Les clés d'authentification Tailscale devenues inutiles ont été révoquées dans la console. L'inventaire d'origine reste dans « Les notes reprises de maintenance.md ». Les identités des nœuds sont distinctes de ces clés.

Le durcissement de SSH a été abandonné. Un contrôle depuis l'extérieur du réseau local, le 2026-10-08, montre que le port 22 est fermé. Le service écoute sur `0.0.0.0:22`, ce qui sert le réseau local et le tailnet. Aucune exposition publique n'a été constatée.

L'onduleur prévu pour le jour du WoL a été abandonné le 2026-10-08. La batterie du laptop suffit à protéger le serveur. La réservation d'adresse IP du serveur reste attachée à la tâche WoL de [todo.md](todo.md).

### Le redémarrage de l'hôte, testé le 2026-10-03

Un `doas reboot` de l'hôte est sans effet sur les deux voies. Au retour, les quatre conteneurs remontent seuls, car tous portent `restart: unless-stopped`. `<OLD-SERVER-NAME>` reprend `<TAILNET-IP-EXIT-DIRECT>` et `<OLD-NODE-EXIT-NYMVPN>` reprend `<TAILNET-IP-EXIT-NYMVPN>`, car leur identité vit dans un volume. Le tunnel Nym se reconnecte seul, en une tentative. L'espace réseau `<OLD-NETNS>` est recréé, avec un identifiant neuf. Les commandes de contrôle sont dans [maintenance.md](maintenance.md).

### Le réglage DNS de l'application iOS

Le test depuis l'iPhone est validé le 2026-10-03, après activation du DNS Tailscale dans l'application iOS. Sans ce réglage, iOS garde le résolveur IPv6 du routeur. L'exit en fail-closed jette alors ces requêtes. Le détail de ce réglage est dans le piège 6.

## Le diagnostic du 2026-10-05 : la mise en service de l'Ethernet

L'utilisateur a acheté un adaptateur USB-C vers RJ45 et l'a branché sur le serveur. Il a constaté que le trafic sortait par le Wi-Fi. Sa constatation était exacte. Ce diagnostic porte sur la sortie Internet, le Wi-Fi et l'Ethernet.

### L'adaptateur est bon, et il était visible depuis le début

L'adaptateur a été mesuré le 2026-10-05. Les mesures ci-dessous viennent d'`ethtool`, de `ip` et du bail DHCP. Le serveur n'a aucun port Ethernet intégré. L'adaptateur est donc la seule option filaire. Il fonctionne.

| Mesure | Valeur |
|---|---|
| Périphérique USB | `0bda:8156` « USB 10/100/1G/2.5G LAN », Realtek RTL8156, sur le port USB 3.x du PCH Intel (`pci 00:14.0`) |
| Pilote | `r8152` v1.12.13, chargé et lié depuis le boot de 18h27 |
| Interface | `eth0`, MAC `<MAC-ETH0>`, ifindex 2 |
| Négociation | 1 Gbit/s full duplex, `Link detected: yes`, `carrier` stable, 0 erreur physique |
| Bail DHCP | `<LAN-IP-SERVER>/24`, passerelle `<LAN-GATEWAY-IP>`, DNS `<LAN-GATEWAY-IP>`, 86400 s |

### Pourquoi il n'était pas utilisé

`/etc/network/interfaces` ne déclarait que `lo` et `wlan0`. Aucun bloc `eth0`. L'interface était donc administrativement down, sans adresse et sans route. Le DHCP n'était jamais lancé. Aucun réglage de l'interface ne pouvait changer cela. Il fallait écrire la configuration. C'est fait, et conservé. Voir « Le correctif retenu » ci-dessous.

### La cause Wi-Fi : le lien change de bande

Le lien sans fil change de bande tout seul. En quelques minutes, `iw dev wlan0 link` est passé de 5260 MHz (5 GHz, canal 52) à 2462 MHz (2.4 GHz, canal 11). Puis il est revenu sur 5 GHz, puis sur 2.4 GHz. Le signal est de -27 dBm. Ce n'est donc pas un problème de couverture.

La gigue qui en découle, mesurée vers `1.1.1.1` sur 30 paquets :

| Lien | min | moy | max | perte |
|---|---|---|---|---|
| Wi-Fi (`wlan0`) | 15,4 ms | 31,9 ms | 69,5 ms | 0 % |
| Ethernet (`eth0`, cible forcée) | 14,4 ms | 15,0 ms | 15,6 ms | 0 % |

Le même phénomène se voit sur le tunnel tailnet, mesuré depuis le Mac : 16,7 / 28,2 / 70,5 ms, écart-type 18 ms. C'est la plainte « ça marche à peu près », quantifiée.

Deux défauts aggravants, le domaine réglementaire et `wpa_supplicant`, restent non corrigés. Leur détail est dans [todo.md](todo.md), section « Les défauts connus, non corrigés ».

### La cause racine : deux interfaces sur le même subnet

Une fois `eth0` monté avec son bail DHCP, la route par défaut bascule seule vers `eth0`, avec un metric plus bas que celui du Wi-Fi. Le trafic sortant se met alors à perdre des paquets par bouffées : des périodes bonnes suivies de périodes à 100 % de perte.

La cause n'est pas la `<ISP-BOX>`. Elle est côté noyau. Une capture le montre :

```text
eth0 :  <LAN-IP-SERVER> > 1.1.1.1   ICMP echo request
wlan0 : 1.1.1.1 > <LAN-IP-SERVER>   ICMP echo reply
```

La requête sort par le câble. La réponse revient par le Wi-Fi. En comptant les ARP :

| `arp_ignore` | demandes `.40` sur eth0 | réponses `.40` sur eth0 | réponses `.40` sur wlan0 |
|---|---|---|---|
| 0 (défaut) | 3 | 0 | 2 |
| 1 | 5 | 0 | 0 |

Le serveur ne répond jamais à l'ARP pour `.40` sur `eth0`. Avec la valeur par défaut, il répond sur `wlan0`. La `<ISP-BOX>` associe donc `.40` à la MAC Wi-Fi. Les retours arrivent par `wlan0`, et `rp_filter=1` les rejette. De là les bouffées.

`arp_ignore=1` ne corrige rien : il supprime la réponse sur `wlan0` sans la rétablir sur `eth0`. `arp_announce=2` est nuisible ici : il choisit « la meilleure adresse locale » d'après la route, qui pointe vers `wlan0`. Les deux sont restés aux valeurs par défaut.

Le déclencheur est l'ambiguïté de `<LAN-SUBNET>`, portée simultanément par `wlan0` et `eth0`. Le noyau résout la route vers la passerelle via `wlan0`. Il émet donc son ARP pour la passerelle depuis la carte Wi-Fi.

### Le correctif retenu

Épingler la route vers la passerelle sur `eth0` :

```sh
ip route replace <LAN-GATEWAY-IP>/32 dev eth0 src <LAN-IP-SERVER> metric 1
```

L'ARP pour la passerelle sort alors par `eth0`. La `<ISP-BOX>` associe correctement `.40` à la MAC filaire. Le trafic est fiable.

Mesures, avec la même boucle de diagnostic (30 tours de `ping` + `curl` vers `1.1.1.1`, un échec = symptôme reproduit) :

| Configuration | Échecs |
|---|---|
| Deux interfaces, sans épinglage | 6 / 10 |
| `eth0` seul (IPv4 de `wlan0` retiré) | 1 / 15 (le premier tour, transitoire) |
| Deux interfaces, épinglage manuel | 0 / 40 |
| Deux interfaces, gardien avec `ip route replace` toutes les 3 s | 4 / 30 |
| Deux interfaces, gardien idempotent | 0 / 30 |

Le `ip route replace` répété supprimait puis recréait la route. Il créait une micro-coupure. Le gardien ne touche donc à la route que si l'état diffère.

### Le repli automatique

Le gardien `/usr/local/bin/uplink-guard` tourne sous `supervise-daemon`. Il est enregistré au runlevel `default`. Sa règle est unique. Si `eth0` est présent, avec son carrier et son adresse IPv4, le gardien épingle la passerelle sur `eth0`. Sinon, il retire l'épinglage et laisse `wlan0` reprendre. `wlan0` n'est jamais coupé.

Repli testé le 2026-10-05 :

| Étape | Routes | Résultat |
|---|---|---|
| `ip link set eth0 down` | épinglage retiré, `wlan0` seul (`metric 303`) | 0 % de perte, HTTP 301, via Wi-Fi |
| `ip link set eth0 up` | épinglage restauré, `eth0` (`metric 202`) prioritaire | 0 % de perte, 14,6 ms, HTTP 301 |

La session SSH n'est pas tombée pendant les deux transitions.

### Les vérifications après correctif

Depuis le serveur, le correctif donne 0 échec sur 30 tours. Le ping `8.8.8.8` montre 14,2 / 14,5 / 14,8 ms. Depuis le Mac, sur le tailnet, les valeurs sont 15,4 / 19,3 / 24,0 ms avec un écart-type de 2,0 ms. Avant le correctif, elles étaient de 16,7 / 28,2 / 70,5 ms avec un écart-type de 18 ms. Le pic est donc passé de 70 ms à 24 ms.

Le redémarrage complet n'a pas été revérifié depuis la reconfiguration réseau du 2026-10-05. Le test du 2026-10-03 avait réussi. Cette vérification reste à faire. Elle est dans [todo.md](todo.md), section « Les défauts connus, non corrigés ».

### La fragilité indépendante, côté Mac

Le diagnostic a trouvé une faiblesse indépendante, côté Mac. Les résolveurs du Mac sont ceux de MagicDNS. Toute résolution de nom dépend donc du Wi-Fi instable. Le contournement prévu est dans [todo.md](todo.md), section « Les défauts connus, non corrigés ».

## La révision des règles du 2026-10-08

L'utilisateur a validé la nouvelle rédaction de [guidelines.md](guidelines.md) avant son application. Les règles ont été réparties entre travail, codage et configuration, documentation et vocabulaire. Les cas techniques particuliers ont rejoint les descriptions et les procédures concernées.

Le glossaire a été simplifié pour définir les concepts sans reprendre la configuration du serveur. Les règles documentaires ont intégré la pertinence, le minimalisme, la précision et la relecture sans contexte. La tâche d'ajout de ces règles a été retirée de [todo.md](todo.md).

## Les sources de la voie 1 versées au dépôt, 2026-10-10

Les sources de `/opt/tailscale` sont désormais versionnées. Le répertoire `tailscale/` du dépôt contient le compose, son gabarit et son `.gitignore`.

Le compose est copié tel quel depuis le serveur. L'image reste épinglée par son digest complet : `tailscale/tailscale@sha256:c507f3a2a6ab1cabd8d809b98edeb41edbd5c3fb6ad9632ffd098b4c7d0b4065`. Le compose ne référence plus aucune variable `TS_AUTHKEY` depuis le 2026-10-03.

Le fichier `/opt/exit-direct/.env` est vide et en mode `600`. Il ne rejoint jamais le dépôt. Le gabarit [.env.example](exit-direct/.env.example) documente qu'aucun secret n'est requis. Un [.gitignore](exit-direct/.gitignore) exclut le `.env`.

L'identité du nœud vit dans le volume `state`. Le compose ne pose que `TS_STATE_DIR` et `TS_EXTRA_ARGS=--advertise-exit-node`. Le projet est donc reconstructible depuis le dépôt.

## Les compléments issus de l'architecture

La date d'origine de ces faits n'est pas consignée. Leur position dans cette chronologie n'est donc pas connue.

Ces constats figuraient dans la description de l'architecture. Les dates ci-dessous sont celles déjà consignées dans cette description. Les passages sans date restent identifiés comme tels.

### Le témoin direct du 2026-09-30

L'adresse publique de la `<ISP-BOX>` valait `<WAN-IP-BOX-A>`. Elle servait de témoin direct pour la sortie de `<OLD-SERVER-NAME>`. Cette adresse était dynamique.

### Les constats de la voie 1 du 2026-10-03

`TS_STATE_DIR` a pris la valeur `/var/lib/tailscale`. La clé d'authentification a été retirée de `/opt/tailscale/.env`, avec sa référence dans le compose. Le test de bout en bout depuis l'iPhone a relevé `<WAN-IP-BOX-B>`, l'adresse de la `<ISP-BOX>`, avec `<OLD-SERVER-NAME>` sélectionné.

### Les constats réseau du 2026-10-05

La partie réseau a été réévaluée. `ethtool` 7.0 et `ifupdown-ng-ethtool` étaient installés comme outils de diagnostic. `uplink-guard` était en service, supervisé au runlevel `default`.

Le fichier `/etc/network/interfaces` portait `auto eth0` et `iface eth0 inet dhcp`, après `wlan0`. Les sauvegardes `/etc/network/interfaces.bak.202610052234` et `.bak.202610052137` étaient présentes. Le récit des essais est dans la section « Le diagnostic du 2026-10-05 : la mise en service de l'Ethernet ».

### La vérification du 2026-10-08

Le fichier `/opt/tailscale/.env` était en mode `600`. Sa variable `TS_AUTHKEY` était vide. Le compose ne référençait plus cette variable.

### La période de vérification de l'inventaire

L'inventaire de la machine indiquait une vérification entre le 2026-10-03 et le 2026-10-08. Cette plage ne datait pas chaque ligne séparément. Les éléments de cet inventaire décrivaient l'état constaté pendant cette période.

L'ancien projet `/opt/nymvpn` était absent. Le port `127.0.0.1:1090` était libre. L'image de la voie directe était notée `tailscale/tailscale@sha256:c507…`. Le digest complet a été relu sur le serveur le 2026-10-08 : `tailscale/tailscale@sha256:c507f3a2a6ab1cabd8d809b98edeb41edbd5c3fb6ad9632ffd098b4c7d0b4065`.

### Les essais et les choix sans date consignée

Un essai de reconnexion était décrit dans l'architecture, sans date. Après un `nym-vpnc disconnect` manuel, le superviseur avait rétabli le tunnel en moins de 12 secondes. Les passerelles étaient restées les mêmes.

Le choix d'un espace réseau dédié protégeait la voie 1 des routes et du pare-feu de la voie 2. Une route ou une règle mal placée dans le réseau de l'hôte pouvait rendre la voie 1 injoignable. L'alternative `network_mode: host` avait donc été écartée pour la voie 2.

Le conteneur dédié évitait de faire porter l'espace réseau par `nym`. Avec `network_mode: service:nym`, une recréation de ce conteneur faisait perdre l'espace partagé. `tailscaled` pouvait rester accroché à l'ancien espace et perdre ses interfaces.

La description expliquait aussi le choix du mode noyau, `TS_USERSPACE=false`. Elle signalait une confusion possible entre les marques `0x80000` et `0x14d` en mode espace utilisateur. Le trafic pouvait alors repartir par la table principale.

La construction locale de Nym avait été retenue faute d'image officielle pour Linux. La description indiquait que le client officiel ne fournissait que des paquets macOS. La version `2026.12.4` était présentée comme la dernière fournissant des binaires Linux.

Le passage du contrôle Tailscale par le mixnet coupait sa connexion au bout de deux minutes. Le choix retenu faisait sortir ce contrôle directement par `eth0`. Le trafic relayé des clients restait dans le tunnel.

Le gabarit documentaire prévoyait `--accept-routes=true` pour les compagnons des futurs services. Sans ce drapeau, le nœud ignorait la route de l'exit node et la bascule restait sans effet. Le résolveur prévu était `100.100.100.100`, pour éviter une résolution par la `<ISP-BOX>` hors du tailnet.

### Les extraits techniques sans date de relevé

Ce relevé figurait dans l'architecture, avec le tunnel connecté. Sa date de mesure n'était pas consignée. Les numéros de priorité changeaient avec les connexions Nym, tandis que l'ordre décrit restait le même.

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

Deux commandes décrivaient les règles posées par le superviseur. Elles figuraient comme extraits d'implémentation. Leur présence ne consignait pas une exécution manuelle.

```
ip rule add priority <n-1> fwmark 0x80000/0xff0000 lookup 1000
ip rule add priority <n-2> to 100.64.0.0/10 lookup 52
```

L'extrait de pare-feu montrait seulement le rejet de fin. Il ne représentait pas toutes les autorisations de la chaîne. La description signalait aussi les autorisations vers `tun0` et les passerelles Nym.

```
chain output  { policy drop; udp dport 53 reject; tcp dport 53 reject with tcp reset; reject; }
chain forward { policy drop; udp dport 53 reject; tcp dport 53 reject with tcp reset; reject; }
```

## Les choix et les décisions repris de philosophy.md

La date d'origine de ces faits n'est pas consignée. Leur position dans cette chronologie n'est donc pas connue.

Ces tableaux figuraient dans [philosophy.md](philosophy.md) avant son recentrage sur les principes. La date d'origine de chaque décision n'était pas consignée. Cette transcription conserve les versions, les justifications et les formulations de la source. Les renvois ont été adaptés au nouvel emplacement.

### Le contexte du choix d'anonymisation

L'ancienne présentation associait la menace au fournisseur d'accès et aux métadonnées. Elle retenait le mode fast, car le mixnet était jugé trop lent. Elle indiquait le géo-bypass désactivé pour ne pas signaler la localisation du client au réseau Nym.

### Les choix technologiques

Le tableau associait chaque technologie à un besoin. Il consignait sa justification et l'alternative refusée. Les descriptions sont celles de la source archivée.

| Technologie | Besoin | Pourquoi celle-ci | Alternative refusée |
|---|---|---|---|
| Alpine 3.24 | Le système d'exploitation | L'utilisateur veut garder Alpine minimal. Il a retiré `ttyd`, `tmux` et le cache des paquets, pour cela et pour des raisons de sécurité. | Une distribution plus lourde |
| Docker et compose | Empiler les microservices | Docker isole les conteneurs. Docker démarre au boot. Les identités vivent dans des volumes qui survivent à une recréation. | Des services natifs Alpine, sans isolation |
| Tailscale | L'accès au serveur et le transport des deux sorties | Le tailnet donne l'accès. Aucun port n'est exposé. Chaque appareil choisit sa sortie dans l'app. | La réservation d'adresse IP locale, réservée au jour du WoL |
| Deux exit nodes | Deux sorties indépendantes | Le choix vaut pour la session. Un appareil ne change pas de voie en cours de session. | Un exit node unique |
| Nym en mode fast | Anonymiser la voie 2 | Son débit convient à un usage quotidien. | Le mixnet, trop lent |
| Espace réseau dédié `<OLD-NETNS>` | Isoler la voie 2 de l'hôte | Une route ou un pare-feu mal placé dans la voie 2 casserait la route de l'hôte. La voie 1 deviendrait injoignable. | `network_mode: host` pour la voie 2 |
| Conteneur `<OLD-NETNS>` dédié | Tenir l'espace réseau | Un espace réseau appartient au conteneur qui le crée. Avec `service:nym`, un redémarrage de `nym` détruirait l'espace. | `network_mode: service:nym` |
| Image `local/tailscale-nft` | Le pare-feu de la voie 2 | L'image officielle pointe `iptables` vers `iptables-legacy`. Le noyau d'Alpine n'expose aucun module `ip_tables`. | L'image officielle Tailscale |
| Backend noyau `TS_USERSPACE=false` | Éviter la confusion des marques | En espace utilisateur, la marque Tailscale `0x80000` et la marque Nym `0x14d` peuvent se confondre. Le trafic repart alors par la table principale. | Le mode espace utilisateur |
| AdGuard Home, phase C | Le filtrage DNS | Le filtrage se fait à la couche DNS, indépendamment du choix d'exit node. | Le résolveur de la `<ISP-BOX>`, qui ferait quitter le tailnet |
| ntfy, phase D | Les notifications | Le choix et le détail des alertes sont dans « Les décisions actées ». | Aucune |
| Un disque exportable | Le stockage | Le choix et sa condition sont dans « Les décisions actées ». | La redondance immédiate |
| Images épinglées par digest et par version | La reproductibilité | Les images distantes sont épinglées par digest. Les images locales le sont par version. | Les images flottantes |
| `tailscaled` compagnon, phase C | Donner une adresse Tailscale à chaque service | La bascule se fait avec `tailscale set`. Elle ne recrée pas le conteneur. | Aucune |

### Les décisions actées

Le tableau conserve les décisions telles qu'elles étaient formulées dans la source. Certaines concernaient des services encore prévus. Le critère d'adresse de sortie concernait le fonctionnement de la voie Nym, pas une preuve complète d'anonymat.

| Domaine | Décision |
|---|---|
| Menace | Deux décisions contre les métadonnées : le mode fast et la désactivation du géo-bypass. Le détail est dans « Le contexte du choix d'anonymisation ». |
| Sortie pour les appareils | Deux exit nodes Tailscale distincts. L'utilisateur choisit dans l'app de chaque appareil. `<OLD-SERVER-NAME>` sort en direct. `<OLD-NODE-EXIT-NYMVPN>` sort par un anonymiseur. |
| Sortie pour les microservices | Un choix par service. Le `tailscaled` du service pointe vers `<OLD-SERVER-NAME>`, vers `<OLD-NODE-EXIT-NYMVPN>`, ou vers aucun exit node. La bascule ne recrée pas le conteneur. |
| Voie 2 | Objectif confirmé du projet. L'agent choisit l'architecture et la documente. Aucune recette préexistante n'est opposable. |
| Preuve de réussite | L'adresse de sortie vue depuis l'iPhone, avec `<OLD-NODE-EXIT-NYMVPN>` sélectionné, n'est pas celle de la `<ISP-BOX>`. Ce test suffit. |
| Droits de l'agent | Écriture libre sur la voie 2. Aucun droit d'écriture sur la voie 1 sans accord de l'utilisateur. |
| Exposition | Les services restent accessibles par le tailnet seulement. Une exposition publique est une décision séparée et différée. |
| Données | Un disque exportable. La redondance sera décidée quand le disque contiendra des données précieuses. |
| Emplacement des services | Un projet compose par service dans `/opt/<service>`. Le répertoire appartient à root. Chaque projet porte son fichier `.env` de secrets, absent du repo. Le fichier `.env.example` sert de gabarit. Les images distantes sont épinglées par digest. Docker stocke les images et les volumes dans `/var/lib/docker`. |
| Méthode | Le résultat doit être fiable et sûr. L'utilisateur veut comprendre chaque mécanisme avant de continuer. |
| Modalité de travail | L'agent propose et agit. L'utilisateur garde la main sur la voie 1. |
| DNS | AdGuard Home devient un microservice. Son résolveur amont suit le choix de sortie du service. |
| Surveillance | Une alerte signale une coupure de l'anonymiseur ou une coupure de courant. Le service de notification est ntfy. |
| Repo | Le repo GitHub est privé. Il contiendra `tailscale-nym/`, `adguard/` et cette documentation. |
| Secrets | Les secrets vivent dans `.env`. Le `.gitignore` reste strict. L'agent ne cherche jamais une clé, une graine ou un mot de passe dans les fichiers de l'utilisateur. Il n'utilise un secret que si l'utilisateur le lui donne. |
| PC gaming | Windows sert au jeu. Linux sert de nœud tailnet, de WoL et d'accès distant. |
| Accès au serveur | Le tailnet donne l'accès. Une réservation d'adresse IP sur le réseau local ne servira qu'au jour du WoL. |

## Les notes reprises de maintenance.md

La date d'origine de ces faits n'est pas consignée. Leur position dans cette chronologie n'est donc pas connue.

Ces notes figuraient dans [maintenance.md](maintenance.md) avant son recentrage sur les procédures réutilisables. Elles décrivaient des essais et préparaient des nettoyages ponctuels. Leur présence ne constituait pas un constat d'exécution du nettoyage.

### Le client de diagnostic du 2026-10-03

La documentation décrivait `ts-client` avec l'image `tailscale/tailscale:stable`, basée sur Alpine 3.22.6. Elle indiquait que l'image ne contenait ni `curl` ni `dig`. Depuis cette date, `loop.sh` installait les outils avec `apk add --no-cache curl bind-tools`.

Le script vérifiait la présence de `ts-client` avant l'installation. Une commande manuelle était prévue si l'installation automatique échouait. Le client servait aux essais de relais entre les deux voies.

La clé de cet essai n'était pas éphémère. Le nœud avait pris le nom `ts-test-1`, car `ts-test` existait déjà. Sa suppression était prévue depuis la console Tailscale.

### Les observations sans date consignée

L'ancien guide distinguait l'adresse du tailnet de l'adresse locale `<LAN-IP-WIFI>`. Il indiquait que l'adresse locale fonctionnait depuis une machine sur place, mais échouait depuis le Mac connecté au tailnet. Il attribuait cet échec à un routage dans un tunnel local au Mac.

Deux règles nft temporaires commentées `TEMPO` étaient décrites comme disparues après les recréations de `nym`. Le contrôle proposé portait sur la chaîne `inet nym forward`. La date de ce contrôle n'était pas consignée.

### L'inventaire préparatoire des clés

Cet inventaire figurait dans la section des clés à révoquer. Il associait les clés aux usages du projet, sans consigner leur révocation. Les références à l'historique shell restent une trace documentaire, pas une consigne de recherche des secrets.

- La clé de `/opt/tailscale/.env`, consommée le 2026-10-03. La source la décrivait comme une clé à usage unique. Elle avait été retirée du fichier `.env` et de `docker-compose.yaml` le 2026-10-03.
- La clé de `/opt/tailscale-nym/.env`, utilisée pour `<OLD-NODE-EXIT-NYMVPN>`.
- La clé du conteneur de test `ts-client` sur le Mac, qui avait créé `ts-test-1`.
- Les clés plus anciennes mentionnées dans `/home/<ADMIN-ACCOUNT>/.ash_history`, notamment aux lignes 58 et 263.

La documentation signalait que `TS_AUTHKEY` apparaissait dans l'environnement de `<OLD-NODE-EXIT-NYMVPN>`. Elle distinguait cet état de celui de `tailscale`, qui ne portait plus de clé depuis le 2026-10-03. Les fichiers `.env` étaient décrits en mode `600`.

### Le reclassement documentaire du 2026-10-08

[philosophy.md](philosophy.md) a été recentré sur les objectifs et les principes. [maintenance.md](maintenance.md) a été réorganisé autour des interventions et de leurs résultats attendus. Les nettoyages ponctuels et la décision sur le DNS de récupération ont rejoint [todo.md](todo.md).

Ce journal a été réorganisé du plus ancien au plus récent. Les sections dont la date n'était pas consignée ont été regroupées à la fin, avec cette mention. Les six pièges de la voie 2 ont été datés et insérés à leur place dans la chronologie.

Les dates des pièges 1, 2, 3, 4 et 5 sont estimées, au 2026-09-30 ou au 2026-10-03. L'estimation a été faite le 2026-10-08 d'après les correctifs relevés sur le serveur. Le piège 6 est daté du 2026-10-03, car son réglage iOS a été validé ce jour-là.

### Les tests lecteurs et les vérifications du 2026-10-08

Trois lecteurs sans historique ont relu les sept fichiers. Le lecteur des procédures a trouvé dix lacunes de contenu, devenues des tâches. Le lecteur de navigation a trouvé un renvoi invalide et des termes non définis. Le lecteur de l'architecture a annoncé des contradictions. Le serveur a infirmé plusieurs d'entre elles : la chaîne `nat` est bien accrochée à `postrouting` et reste vide, et les priorités 5206, 5207 et 5208 confirment le calcul annoncé.

Le serveur a confirmé le mode espace utilisateur de la voie 1, avec l'option `--tun=userspace-networking` et aucune interface `tailscale0` sur l'hôte. Il a confirmé le refus du port 53 par les règles nft de Nym. Il a confirmé une MTU effective de 1340 octets sur la voie 2, mesurée sur du trafic réel. Il a fourni le digest complet de l'image de la voie 1, absent du journal avant ce jour.

Les changements ont été enregistrés en sept commits le 2026-10-08, un par périmètre. La réorganisation de la documentation est terminée. La tâche correspondante a été retirée de [todo.md](todo.md).

### Le renommage des vingt-quatre identifiants du 2026-10-10

Le plan committé dans [todo.md](todo.md) (voie 2 puis voie 1) a été exécuté sans piège. Les trois couches — clé de service, `container_name`, hostname de nœud — ont été renommées sur le serveur puis dans le dépôt, deux commits, un par palier.

La voie 2 est devenue `exit-nymvpn` : projet `/opt/exit-nymvpn`, services `netns-nymvpn`, `tunnel-nymvpn`, `exit-nymvpn`, `--hostname=exit-nymvpn`. Le nœud a gardé `<TAILNET-IP-EXIT-NYMVPN>`. La voie 1 est devenue `exit-direct` : projet `/opt/exit-direct`, conteneur `exit-direct`, `--hostname=exit-direct`. Le nœud a gardé `<TAILNET-IP-EXIT-DIRECT>` et l'ancien nœud `<OLD-SERVER-NAME>` n'existe plus.

Le CLI Docker 29.5.3 ne propose pas `docker volume rename`. Les migrations ont été faites par `volume create` puis copie byte-identique (`cp -a` via alpine), contrôlée par `diff -r` et un hash SHA-256 agrégé identique. Les identités persistantes ont traversé la migration sans changement.

Le client de diagnostic `ts-client` a été recréé sur le Mac avec une clé d'authentification éphémère fournie par l'utilisateur. Le nœud `ts-test` s'est enregistré en `<TAILNET-IP-TS-TEST>`. La boucle de relais a donné le contrôle `exit-direct` fonctionnel et un verdict `VERT` sur la cible `exit-nymvpn` : l'IP de sortie passe de `<WAN-IP-BOX-A>` (`<ISP-BOX>`) à `57.131.28.186` (passerelle Nym).

Les volumes orphelins ont été supprimés par noms exacts après le vert final : `tailscale-nym_state`, `tailscale-nym_nym-data`, `tailscale-nym_ts-sock`, `tailscale_state`. Restent les volumes `exit-direct_state` et `exit-nymvpn_state`, `exit-nymvpn_nym-data`, `exit-nymvpn_ts-sock`.

Restent des gestes côté clients à la reconnexion : démarrer Tailscale sur le Mac, vérifier l'SSH par le tailnet (`<TAILNET-IP-EXIT-DIRECT>`), reconnecter et re-sélectionner `exit-nymvpn` (et `exit-direct` en sortie directe) sur `<HOST-IPHONE>` et `<HOST-MACBOOK>`.

### Le retour de `<HOST-MACBOOK>` sur le tailnet du 2026-10-10

Le client Tailscale du Mac a été redémarré dans la soirée. L'identité conservée a repris sa place : `<HOST-MACBOOK>` en `<TAILNET-IP-CLIENT>`. La sortie directe `exit-direct` a été sélectionnée comme exit node, avec `ExitNodeAllowLANAccess` actif pour préserver l'accès au réseau local.

L'SSH par le tailnet a été validé de bout en bout depuis le Mac : `ssh <ADMIN-ACCOUNT>@<TAILNET-IP-EXIT-DIRECT>` répond. L'SSH par le LAN reste fonctionnel. `tailscale ping` vers `exit-direct` répond en quelques millisecondes.

À la reconnexion du téléphone, `<HOST-IPHONE>` reprendra sa place et devra re-sélectionner une sortie dans l'app (par exemple `exit-nymvpn` pour la voie anonymisée).

## La publication du dépôt, 2026-10-11

Le dépôt est passé de privé à public. Le compte GitHub et le pseudonyme d'écriture sont conservés. La licence est MIT, au nom de `Eli`. L'adresse est <https://github.com/Bonnet2B1/home-server>.

La décision reprise de `philosophy.md` — « Le repo GitHub est privé. Il contiendra `tailscale-nym/`, `adguard/` et cette documentation. » — est dépassée sur deux points. Le dépôt est public. Le dossier `tailscale-nym/` est devenu `exit-nymvpn/` le 2026-10-10.

### Le masquage avant publication

Les valeurs qui identifient l'utilisateur ou son réseau ne sont pas publiées en clair. Chacune est remplacée par un jeton stable, défini dans `sanitize.map`. Ce fichier est ignoré par Git : il ne suit pas le dépôt.

Un filtre Git fait la conversion dans les deux sens. Au commit, `redact` remplace les valeurs réelles par les jetons. À la récupération des fichiers, il fait l'inverse. L'arbre de travail garde donc les valeurs réelles. Un hook `pre-commit` refuse un commit dont l'index contient une valeur sensible. Il refuse aussi un jeton écrit en prose sans backticks. Les règles sont dans [guidelines.md](guidelines.md), section « Le masquage avant publication ».

### L'anonymisation de l'historique

Les vingt-huit commits d'origine ont été réécrits : contenu, auteur et message. Les dates d'auteur et de commiteur sont conservées. Tous les commits portent l'identité `Eli <eli@users.noreply.github.com>`, qui remplace l'adresse personnelle d'origine.

Les sommes de contrôle de tous les commits changent. L'historique d'origine ne subsiste que dans une sauvegarde locale. Les refs internes de l'agent contenaient l'historique non anonymisé. Elles ont été supprimées, avec le reflog et les objets orphelins, avant la publication. Seule `main` a été poussée.

### Les pseudonymes

Le compte GitHub et le pseudonyme d'écriture sont distincts. Le nom du tailnet figure dans l'URL du dépôt. Il est donc public, et le masquer n'ajouterait rien. Il reste en clair dans la documentation. Le domaine du tailnet reste masqué.

Le nom seul ne donne aucun accès. Rejoindre le tailnet demande une invitation. MagicDNS ne répond pas hors du tailnet. Aucun service n'est exposé publiquement.

### Le rendu sur GitHub

Deux effacements ont été constatés au rendu. Un jeton écrit en prose est traité comme du HTML brut et disparaît. Un jeton dans un diagramme est pris pour une balise et disparaît aussi. Les entités HTML ne sauvent rien dans un fichier Markdown : le rendu Markdown échappe le caractère `&` avant de passer le bloc à Mermaid.

Le schéma d'`architecture.md` était dessiné à la main, en largeur fixe. Le masquage a décalé ses cadres. Il a été remplacé par un diagramme Mermaid, rendu par GitHub, avec les jetons entre guillemets.

### Le dépôt public

Le dépôt contient trente-deux commits et trente-deux fichiers. Un clone neuf du dépôt public ne contient aucune valeur masquée, dans les arbres comme dans les messages de commit. Il n'expose que `main`. Les étapes et les critères ont été inscrits dans [todo.md](todo.md) avant le travail, puis retirés une fois vérifiés, conformément au cheminement d'une modification défini dans [guidelines.md](guidelines.md).

## L'incident du logbook tronqué, 2026-10-11

La consignation de la publication a d'abord échoué. Un script de consignation a réécrit `logbook.md` au lieu d'ajouter la section : le fichier est tombé de 501 à 35 lignes.

Le commit fautif, `f802ca2`, a été poussé avant la vérification. Pendant quelques minutes, le dépôt public montrait un logbook réduit à la seule section de publication. La vérification des renvois a révélé l'écart : la décision « Le repo GitHub est privé », attendue au tableau des choix, manquait.

Le fichier sain a été restauré depuis l'historique, puis la section ajoutée en mode ajout. Le diff avec la version saine compte trente-quatre lignes ajoutées et aucune supprimée. Le commit `2a6529d` répare l'état. Le commit fautif reste dans l'historique public : l'incident y demeure lisible.

Aucune valeur sensible n'a été exposée. La perte était une disparition de contenu, pas une fuite. La leçon : le contrôle avant un push porte sur les fuites, mais aussi sur la forme des fichiers. Un comptage de lignes aurait suffi à l'arrêter.

## Les corrections de l'outillage, le 2026-10-11

Quatre audits indépendants ont passé en revue le dépôt publié, le masquage et l'outillage. Le dépôt public ne contenait aucune valeur identifiante. L'outillage présentait des défauts, corrigés le jour même.

Un contrôle vient s'ajouter au hook `pre-commit` : un hook `commit-msg` refuse un message de commit qui contient une valeur réelle ou un jeton écrit en prose sans backticks. `check_leaks.py` ne plante plus sur une adresse invalide, et les fichiers binaires ne lui échappent plus : il y cherche les valeurs à fort signal. La détection des adresses MAC accepte les tirets, pas seulement les deux-points. Le filtre et le hook partagent la même règle de frontière : une valeur collée à un autre caractère est masquée, donc le commit n'est plus bloqué sans issue. Les jetons dans un lien Markdown ou dans une URL ne sont ni backtiqués ni signalés. `rewrite_history.py` gère les fusions et refuse d'écraser la branche `sanitize` sans `REWRITE_FORCE=1`. La couverture du filtre s'étend aux `*.py`, à `.gitignore`, à `.dockerignore`, à `LICENSE` et aux hooks.

La section « Les défauts connus, non corrigés » de [todo.md](todo.md) est retirée : un défaut connu devient un travail fait immédiatement, pas une catégorie d'attente. Le chiffre « vingt-quatre commits d'origine » est corrigé en « vingt-huit », le compte relevé dans la sauvegarde.

## La surveillance de l'adresse publique, 2026-10-11

L'adresse publique de la box peut changer sans prévenir. La table `sanitize.map` ne connaît que les valeurs écrites. Une adresse nouvelle échappe au filtre et au hook. Un contrôle automatisé comble ce trou.

`tools/wan_ip.py` a deux modes. `check` lit l'adresse publique actuelle et vérifie qu'elle est couverte par la table. Il bloque un commit dont l'index contient cette adresse en clair. Sans réseau, il prévient et ne bloque pas. `update` remplace la valeur réelle du jeton de la box A dans `sanitize.map`.

Le hook `pre-commit` exécute le contrôle après `check_leaks.py`. La section « Les règles Git et de push » de [guidelines.md](guidelines.md) rassemble les règles de poussée liées à la confidentialité.

Le contrôle a été vérifié sur dix scénarios, dont le blocage bout en bout d'un commit qui contenait l'adresse courante en clair. Le contrôle en conditions réelles du jour : l'adresse publique actuelle est couverte par la table.

## La validation par les sous-agents, le 2026-10-12

Une règle de validation est ajoutée à [guidelines.md](guidelines.md), section « Le cheminement d'une modification ». Une tâche n'est validée qu'après un audit en lecture seule par des sous-agents. L'audit reprend chaque critère et rend des constats par gravité. L'agent vérifie chaque constat avant de valider. Le nombre de sous-agents s'adapte au travail : un par partie au besoin. La règle généralise la pratique des quatre audits du 2026-10-11.

## La correction du contrôle des messages, le 2026-10-12

L'audit des sous-agents du jour a relevé un écart : le hook `commit-msg` ne contrôlait pas les adresses IP et MAC dans le message, alors que le hook `pre-commit` les contrôlait dans l'index. Une adresse publique nouvelle, absente de la table, écrite dans un message de commit échappait à toutes les mailles.

Correction du jour : `check_message` passe par les mêmes contrôles que l'index, valeurs réelles, IP, MAC, secrets et jetons compris. `wan_ip.py check` accepte un fichier de message (`--text`) et bloque un message qui contient l'adresse publique actuelle en clair. Le hook `commit-msg` exécute les deux contrôles. La couverture est vérifiée sur treize scénarios, dont le blocage bout en bout par `wan_ip check --text`.

## L'abandon du filtrage DNS, 2026-10-12

Le filtrage publicitaire au niveau DNS est abandonné. La conception prévoyait un résolveur AdGuard Home sur le serveur, déclaré en nameserver global du tailnet, avec un conteneur compagnon Tailscale et un amont en DoT ou DoH.

L'utilisateur a demandé l'abandon le 2026-10-12. La conception reposait sur une chaîne de décisions prises avant la compréhension du mécanisme DNS. Une fois ce trajet compris, l'utilisateur a jugé cette chaîne bâtie sur des réponses données sans connaissance, donc sans valeur. Il a préféré l'effacer plutôt que la poursuivre.

Ce qui a été retiré du dépôt :

- Le dossier `adguard/` : le compose, `verif.sh`, `.env.example` et `.gitignore`.
- La tâche « Le réglage DNS d'AdGuard Home » de [todo.md](todo.md).
- La tâche « Le microservice AdGuard Home » de [todo.md](todo.md).
- La ligne correspondante de [readme.md](readme.md).

Ce qui a été conservé et détaché d'AdGuard, car une autre tâche s'en sert :

- Le gabarit d'un microservice, devenu la section du même nom dans [todo.md](todo.md). La tâche WoL s'y réfère.
- La tâche « Les modes d'accès d'un microservice », qui vaut pour WoL.

Rien n'a été retiré du serveur. AdGuard Home n'a jamais été déployé et `verif.sh` n'a jamais été exécuté. Aucun conteneur, volume, image ni nœud de tailnet ne porte ce nom.

Les décisions antérieures qui portaient sur AdGuard restent consignées comme historique : la ligne du tableau « Les choix technologiques » (AdGuard Home, phase C) et la ligne « DNS » des « décisions actées ». Elles sont caduques à compter de cette date.
