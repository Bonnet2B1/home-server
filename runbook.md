# Runbook : les événements passés

Ce fichier raconte ce qui s'est passé sur le serveur. Il contient les incidents, les diagnostics et les pièges. L'état actuel de la machine est dans `architecture.md`. Les tâches restantes sont dans `todo.md`.

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

Ces étapes reprennent l'accès, avec un accès physique ou distant :

1. Lisez `docker ps -a` et le STATUS réel du conteneur.
2. Lisez les journaux du projet avec `cd /opt/tailscale && docker compose logs --tail 80`. Cherchez `NeedsLogin`, `network is unreachable`, `no such host` ou un `panic`.
3. Vérifiez la route et le DNS de l'hôte : `ip -4 route`, `cat /etc/resolv.conf`, `ping -c2 1.1.1.1`.
4. Si `/etc/resolv.conf` de l'hôte pointe vers `100.100.100.100`, remettez-le sur un résolveur public.
5. Recréez le conteneur avec `cd /opt/tailscale && docker compose up -d --force-recreate`. L'état du nœud vit dans le volume `state` et survit.

Leçon : la voie 1 et la voie 2 vivent sur le même hôte. Un motif de nom commun frappe les deux. La règle qui en découle est dans `guidelines.md`, section « Docker ».

### La résolution du 2026-10-03

L'accès distant est revenu par le réseau local. Le diagnostic a montré trois causes côté voie 1.

1. Le compose de la voie 1 montait le volume `state`, mais ne posait pas `TS_STATE_DIR`. `containerboot` démarrait donc avec `--state=mem:`. L'identité du nœud vivait en mémoire. Chaque recréation du conteneur perdait l'identité.
2. Aucune clé d'authentification ne restait pour reconstruire l'identité.
3. `containerboot` donne 60 secondes à `tailscale up`. Sans clé, l'enregistrement attend une validation par URL. Le délai expire. `containerboot` arrête `tailscaled`. Le conteneur sort avec le code 0. `restart: unless-stopped` le relance. Chaque cycle produit une nouvelle URL. La boucle interdit toute connexion par URL.

Le diagnostic a relevé une seconde cause, côté voie 2 : le superviseur écrivait sa règle de masquerade dans `inet nym postrouting`. Cette chaîne n'existe pas. L'écriture échouait en silence et le journal annonçait un faux succès toutes les 30 secondes. Le bloc a été retiré le 2026-10-03. Voir « Le pare-feu Nym » de `architecture.md` pour le détail.

Le correctif au compose pose `TS_STATE_DIR=/var/lib/tailscale` et `TS_AUTHKEY=${TS_AUTHKEY}`. La première variable rend l'identité persistante. La seconde enregistre le nœud immédiatement. La clé vit dans `/opt/tailscale/.env`, en mode `600`.

Après le correctif, `tailscaled.state` apparaît dans le volume. Un `docker restart tailscale` laisse le nœud en ligne, avec la même adresse. Le journal affiche `machineAuthorized=true; authURL=false`.

L'ancien nœud `<OLD-SERVER-NAME>` a été supprimé dans la console. Le nouveau nœud a repris le nom `<OLD-SERVER-NAME>` et l'adresse `<TAILNET-IP-EXIT-DIRECT>`. L'ancienne adresse `<TAILNET-IP-OLD-IDENTITY>` ne sert plus.

## La validation des deux voies, 2026-10-03

Les deux voies ont été validées le 2026-10-03. La liste ci-dessous donne les critères de réussite, relevés ce jour-là. Une seule case reste non cochée, et sa tâche est dans `todo.md`.

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

### Le redémarrage de l'hôte, testé le 2026-10-03

Un `doas reboot` de l'hôte est sans effet sur les deux voies. Au retour, les quatre conteneurs remontent seuls, car tous portent `restart: unless-stopped`. `<OLD-SERVER-NAME>` reprend `<TAILNET-IP-EXIT-DIRECT>` et `<OLD-NODE-EXIT-NYMVPN>` reprend `<TAILNET-IP-EXIT-NYMVPN>`, car leur identité vit dans un volume. Le tunnel Nym se reconnecte seul, en une tentative. L'espace réseau `<OLD-NETNS>` est recréé, avec un identifiant neuf. Les commandes de contrôle sont dans `operations.md`.

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

Deux défauts aggravants, le domaine réglementaire et `wpa_supplicant`, restent non corrigés. Leur détail est dans `todo.md`, section « Les défauts connus, non corrigés ».

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

Le redémarrage complet n'a pas été revérifié depuis la reconfiguration réseau du 2026-10-05. Le test du 2026-10-03 avait réussi. Cette vérification reste à faire. Elle est dans `todo.md`, section « Les défauts connus, non corrigés ».

### La fragilité indépendante, côté Mac

Le diagnostic a trouvé une faiblesse indépendante, côté Mac. Les résolveurs du Mac sont ceux de MagicDNS. Toute résolution de nom dépend donc du Wi-Fi instable. Le contournement prévu est dans `todo.md`, section « Les défauts connus, non corrigés ».

## Les pièges de la voie 2

Ces obstacles ont bloqué la mise en service de la voie 2. Chacun a une cause précise et distincte des autres. Le correctif de chaque piège est décrit dans son paragraphe.

##### Piège 1 : sendmmsg: operation not permitted à la poignée de main

Le client Nym pose ses règles nft après avoir démarré WireGuard. La première poignée de main arrive donc avant que les règles ne l'autorisent. Elle tombe sur la règle `reject` finale. Le noyau renvoie un `EPERM` au processus local. C'est le bug amont [6303](https://github.com/nymtech/nym-vpn-client/issues/6303), dont le correctif [6238](https://github.com/nymtech/nym-vpn-client/pull/6238) n'est pas fusionné. Le correctif utilisé est `"netstack": true`. Il remplace l'interface du second saut par une pile réseau en espace utilisateur, ce qui supprime le conflit. Après ce réglage, le compteur d'erreurs `sendmmsg` tombe à zéro.

##### Piège 2 : Failed to apply src_valid_mark: Read-only file system

Nym doit marquer les paquets reçus du tunnel pour que sa propre règle de routage les exclue de la table 333. Docker monte `/proc/sys` en lecture seule, donc l'écriture échoue, et le tunnel ne se monte jamais. Le correctif passe par `sysctls` du compose, sur `net.ipv4.conf.default`. Une interface créée ensuite hérite de ces valeurs, au moment où Nym crée `tun0`. Cette méthode évite d'ajouter la capacité `SYS_ADMIN` au conteneur. Sans ce réglage, la connexion reste bloquée à l'étape `registering with gateways`.

##### Piège 3 : Disconnected pris pour un état transitoire

Dans le premier superviseur, le motif `*Disconnect*` couvrait aussi `Disconnected`. Le superviseur croyait le tunnel en cours de connexion. Il n'appelait jamais `nym-vpnc connect`. Séparez les états transitoires réels, `Connecting`, `Reconnecting`, `Registering`, `Resolving` et `Unregistering`, de l'état stable `Disconnected`. L'état stable doit déclencher une tentative.

##### Piège 4 : le nœud Tailscale ne pouvait pas s'enregistrer

Le symptôme était trompeur, un RST et non un délai. Le plan de contrôle renvoyait `connection refused`, donc un rejet actif, pas un blocage. La cause : `tailscaled` marque son propre trafic avec `0x80000`. Ses règles le routent vers la table principale, donc vers `eth0`. Or la chaîne `output` de Nym est en `policy drop`. Elle n'autorise que `oif "tun0"` et les passerelles de Nym. Tout le reste tombe sur le `reject` final.

Nym n'offre aucun paramètre pour désactiver son pare-feu. La recherche de chaînes dans le binaire l'a confirmé. Deux contournements étaient possibles. Le premier, ajouter une règle `accept` dans la chaîne `output` de Nym, est à écarter. Nym réapplique son pare-feu à chaque connexion et effacerait la règle. Le second, faire entrer le trafic marqué par le tunnel, est retenu.

L'arrangement des règles `ip rule` qui applique ce contournement est décrit dans « Le routage mesuré » de `architecture.md`.

##### Piège 5 : le nœud passait hors ligne dès son approbation comme exit node

Le nœud était enregistré et en ligne. L'approbation comme exit node l'a fait basculer hors ligne. Le symptôme était un `context canceled` sur l'interrogation du plan de contrôle. C'est une panne de synchronisation, pas une panne réseau, le tunnel étant sain. Deux causes se cumulaient.

La première : `tailscaled` n'arrivait pas à installer ses règles de pare-feu.

```
running [/usr/sbin/iptables -t filter -N ts-input --wait]: exit status 3:
  iptables v1.8.11 (legacy): can't initialize iptables table `filter'
```

L'image Tailscale officielle pointe `/usr/sbin/iptables` vers `iptables-legacy`. Le noyau `6.18.53-0-lts` d'Alpine compile le support iptables en dur. Il ne fournit aucun module `ip_tables` dans `/lib/modules`. L'iptables legacy ne peut donc jamais fonctionner sur cet hôte. `tailscaled` n'a ni option de ligne de commande ni variable d'environnement pour choisir son backend. La voie 1 n'a jamais eu ce problème parce qu'elle tourne en mode espace utilisateur. Le mode espace utilisateur n'installe aucune règle de pare-feu. Le correctif est l'image dérivée `local/tailscale-nft:1.102.5`. Elle repointe les liens symboliques vers `iptables-nft` et `ip6tables-nft`, déjà présents dans l'image.

La seconde : `tailscaled` signalait `Subnet routing is enabled, but IP forwarding is disabled`, alors que `net.ipv4.ip_forward` valait bien 1. La cause est IPv6. Tailscale refuse d'annoncer `0.0.0.0/0` sans `::/0`. Les deux routes sont donc toujours publiées. Son contrôle exige alors le forwarding IPv6, qui valait 0. Le correctif ajoute `net.ipv6.conf.all.forwarding` et `net.ipv6.conf.default.forwarding` aux sysctl du compose.

Activer le forwarding IPv6 n'ouvre aucune fuite. Le namespace n'a aucune route IPv6 par défaut. Il n'a que des adresses lien-local et le préfixe unique local du tailnet sur `tailscale0`. Un paquet IPv6 d'un client n'a nulle part où aller. La chaîne `output` de Nym est en `policy drop`. Le comportement reste fail-closed. Si un jour vous ajoutez une sortie IPv6, ce raisonnement ne vaut plus. Rouvrez alors le dossier.

##### Piège 6 : le client iOS perdait l'internet par le DNS local

Le Mac, client de la même voie, résolvait par MagicDNS en IPv4. Il sortait normalement. Le téléphone, lui, envoyait ses requêtes DNS au résolveur IPv6 du routeur. Ce résolveur est un préfixe global. Le téléphone le routait donc dans le tunnel. L'exit n'a aucune route IPv6. Les requêtes tombaient dans le vide, sans réponse. Le téléphone perdait toute résolution, donc tout l'internet. Le Mac différait sur un seul point : `scutil --dns` montrait `100.100.100.100` sur `utun8`, alors que le téléphone gardait le DNS du routeur.

La cause est un réglage du client. L'application iOS n'activait pas son option DNS. iOS continuait donc d'utiliser le résolveur appris sur le Wi-Fi. Après activation du DNS Tailscale, iOS utilise MagicDNS, résout en IPv4, et l'internet revient. Contrôle : une capture sur `tailscale0` ne montre plus que des flux IPv4 du client. Avant le réglage, la même capture ne montrait que des requêtes DNS IPv6 vers le routeur, sans réponse.

## L'archive : les mesures de l'essai du 2026-09-29

Ces mesures viennent de l'essai de la voie 2, avec l'architecture qui a échoué, et d'un tunnel Nym. Elles peuvent être fausses pour une autre architecture. Certaines peuvent venir de cette architecture plutôt que du fournisseur d'anonymisation. Utilisez-les comme des pistes, jamais comme des propriétés établies. Revalidez chaque chiffre avant de vous y fier.

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
- Le client Nym échoue parfois au handshake avec `sendmmsg: operation not permitted`. Le paramètre `"netstack": true` dans sa configuration corrige ce symptôme. L'issue [3658](https://github.com/nymtech/nym-vpn-client/issues/3658) rapporte la même erreur. Elle est fermée sans correctif. Le symptôme est confirmé le 2026-09-30. La cause réelle est plus précise : voir le piège 1, ci-dessus, avec l'issue [6303](https://github.com/nymtech/nym-vpn-client/issues/6303).
- Le client Nym peut écrire ses propres règles `nft` dans son espace réseau. Un exit node qui partage cet espace doit en tenir compte. Sinon, son trafic est détruit à l'envoi, avant même de sortir.
- Le tunnel Nym s'est arrêté de lui-même le 2026-09-28 alors que ses conteneurs se déclaraient `healthy`. Surveillez l'état réel du tunnel, pas l'état de santé des conteneurs.
- Une exception pare-feu ajoutée à la main dans l'espace réseau ne survit pas au redémarrage du conteneur qui l'a créée. Tout correctif en mémoire demande une réinjection. Il crée donc une dépendance à l'ordre de démarrage. C'est une source d'instabilité. Traitez-la comme un défaut, pas comme une étape.

## Le retrait de ttyd et de tmux, 2026-09-28

Une ancienne session web utilisait `ttyd` et `tmux` sur le port 7681. L'utilisateur a demandé sa suppression le 2026-09-28, pour garder Alpine minimal et pour des raisons de sécurité. La suppression a retiré `ttyd`, `tmux` et le cache des paquets.
