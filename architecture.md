# Architecture : l'état présent du serveur

Ce fichier décrit ce qui existe aujourd'hui et la façon dont c'est construit. Pour savoir ce qui s'est passé, lisez `runbook.md`. Pour savoir ce qui reste à faire, lisez `todo.md`.

## L'état réel de la machine

Cette section décrit ce qui existe réellement sur le serveur. Elle a été vérifiée entre le 2026-10-03 et le 2026-10-08. Elle prime sur les six autres fichiers. Vérifiez-la avant d'agir, car elle peut être périmée.

| Élément | État | Emplacement |
|---|---|---|
| Alpine 3.24, nom d'hôte `<OLD-SERVER-NAME>` | présent | aucun |
| Docker 29.5.x, compose v5.1.4 | présents, démarrent au boot | aucun |
| Utilisateur `<ADMIN-ACCOUNT>` avec `doas` | présent | aucun |
| `<OLD-SERVER-NAME>`, exit node direct | en ligne, `<TAILNET-IP-EXIT-DIRECT>`, identité persistante | `/opt/tailscale`, conteneur `tailscale` |
| `<OLD-NODE-EXIT-NYMVPN>`, exit node anonymisé | en ligne, `<TAILNET-IP-EXIT-NYMVPN>`, tunnel Nym connecté | `/opt/tailscale-nym`, conteneurs `<OLD-NETNS>`, `nym`, `<OLD-NODE-EXIT-NYMVPN>` |
| NymVPN, ancien projet | retiré le 2026-09-29 | `/opt/nymvpn` absent |
| Port `127.0.0.1:1090` | libre | aucun |
| Adaptateur USB-C vers RJ45, Realtek RTL8156 | en service comme `eth0`, `<LAN-IP-SERVER>`, 1 Gbit/s | port USB du PCH Intel |
| `wlan0` | associé, repli automatique, `<LAN-IP-WIFI>/24`, `metric 303` | aucun |
| Route par défaut | passe par `eth0`, `metric 202`, passerelle `<LAN-GATEWAY-IP>` épinglée sur `eth0` | aucun |
| `/etc/network/interfaces` | porte `auto eth0` et `iface eth0 inet dhcp`, après `wlan0` | `/etc/network/interfaces` |
| `ethtool` 7.0 et `ifupdown-ng-ethtool` | installés le 2026-10-05, binaires de diagnostic | aucun |
| `uplink-guard`, épinglage de la passerelle | en service le 2026-10-05, supervisé, runlevel `default` | `/usr/local/bin/uplink-guard`, `/etc/init.d/uplink-guard` |
| Sauvegardes de la configuration réseau | présentes | `/etc/network/interfaces.bak.202610052234`, `.bak.202610052137` |
| Écoute SSH | `0.0.0.0:22`, en attente de durcissement | `/etc/ssh/sshd_config` |
| Batterie | gonflée, châssis déformé, débranchement planifié | aucun |

La partie réseau a été réévaluée le 2026-10-05. Le récit et les mesures sont dans `runbook.md`, section « Le diagnostic du 2026-10-05 : la mise en service de l'Ethernet ».

Les deux voies vivent sur le même hôte. La voie 1 tourne dans le réseau de l'hôte. La voie 2 tourne dans un espace réseau dédié. Le conteneur `<OLD-NETNS>` tient cet espace. Un redémarrage de l'hôte remet les deux voies en ligne sans intervention. Les conteneurs portent `restart: unless-stopped`. Les identités vivent dans des volumes.

Les causes racines des incidents du 2026-10-01 et du 2026-10-03 sont dans `runbook.md`.

## L'architecture générale

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
   │  VOIE 1 - DIRECTE   │        │  VOIE 2 - ANONYMISÉE │
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
 │  MacBook <HOST-MACBOOK>     │          │  son tailscaled :    │
 │  choix dans l'app :   │          │  --exit-node=<OLD-SERVER-NAME>    │
 │  <OLD-SERVER-NAME>  ou <OLD-NODE-EXIT-NYMVPN>    │          │  --exit-node=<OLD-NODE-EXIT-NYMVPN>│
 └───────────────────────┘          │  --exit-node=none    │
                                    └─────────────────────┘
```

Les deux voies sont parallèles. Elles ne se rejoignent jamais. Le point de choix en amont décrit le rôle des deux nœuds. Il ne décrit pas un routeur.

`<OLD-SERVER-NAME>` utilise `network_mode: host`. Il ne partage l'espace réseau d'aucun autre service. Il ne voit aucun tunnel. Le nœud de la voie 2 a sa propre table de routage. Le choix entre les deux voies est donc possible.

Le tailnet et les microservices sont sur le même niveau. Le tailnet donne accès aux nœuds pour les appareils de l'utilisateur. Les microservices donnent accès à leurs applications.

Un microservice choisit sa sortie avec le paramètre `--exit-node` de son `tailscaled`. Un appareil choisit sa sortie dans l'app Tailscale. Le choix vaut pour la session. Un appareil ne peut pas changer de voie en cours de session.

## La voie 1 : `<OLD-SERVER-NAME>`, sortie directe, en service

- Le projet compose `/opt/tailscale` existe. Son image est épinglée, `tailscale/tailscale@sha256:c507…`. Le service utilise `network_mode: host`, les capacités `NET_ADMIN` et `NET_RAW`, et `/dev/net/tun`. Il porte le volume `state` et `restart: unless-stopped`.
- Le nœud `<OLD-SERVER-NAME>` est enregistré en `<TAILNET-IP-EXIT-DIRECT>`. `TS_STATE_DIR` vaut `/var/lib/tailscale` depuis le 2026-10-03. L'identité survit donc à un redémarrage.
- Le fichier `/opt/tailscale/.env` est en mode `600`. La clé qu'il contenait a été retirée le 2026-10-03, avec sa référence dans le compose. Vérifié le 2026-10-08 : la variable `TS_AUTHKEY` est vide.
- L'exit node est approuvé dans la console d'administration Tailscale.
- Le test de bout en bout est fait : depuis l'iPhone, choisissez `<OLD-SERVER-NAME>`, puis ouvrez `https://api.ipify.org`. L'adresse affichée est celle de la `<ISP-BOX>`, `<WAN-IP-BOX-B>` au 2026-10-03.

Le tailnet s'appelle Bonnet2B1. Il contient l'iPhone `<HOST-IPHONE>` et le MacBook `<HOST-MACBOOK>`.

## La voie 2 : `<OLD-NODE-EXIT-NYMVPN>`, sortie anonymisée, en service

L'objectif est d'obtenir un nœud `<OLD-NODE-EXIT-NYMVPN>` du tailnet, approuvé comme exit node. Ce nœud fait sortir le trafic par un anonymiseur. L'iPhone le propose alors à côté de `<OLD-SERVER-NAME>` dans l'app Tailscale.

Le tunnel Nym fonctionne. Il sort par une adresse qui change à chaque nouvelle connexion, car les passerelles sont éphémères. Le témoin direct est la `<ISP-BOX>`, l'adresse de sortie de `<OLD-SERVER-NAME>`. Cette adresse est dynamique. Elle valait `<WAN-IP-BOX-A>` le 2026-09-30. Elle valait `<WAN-IP-BOX-B>` le 2026-10-03. Mesurez-la au moment du test, ne la supposez pas. Le nœud `<OLD-NODE-EXIT-NYMVPN>` est enregistré dans le tailnet en `<TAILNET-IP-EXIT-NYMVPN>` et approuvé comme exit node.

Les deux voies partagent le même hôte. Un exit node relaie le trafic des autres appareils. Une route par défaut mal placée dans l'espace réseau de la voie 2 peut casser la route de l'hôte. Une règle de pare-feu mal placée peut faire de même. La voie 1 deviendrait alors injoignable. Cette raison interdit `network_mode: host` pour la voie 2.

### L'architecture retenue

Un conteneur `<OLD-NETNS>` tient l'espace réseau. Il ne fait rien d'autre que dormir. `nym` et `<OLD-NODE-EXIT-NYMVPN>` le rejoignent avec `network_mode: service:netns`. Les trois partagent donc les mêmes interfaces, les mêmes tables de routage et les mêmes règles nft.

Le conteneur dédié évite un piège. Un espace réseau appartient au conteneur qui le crée. Avec `network_mode: service:nym`, un simple redémarrage de `nym` détruirait l'espace. `tailscaled`, resté accroché à l'ancien, perdrait ses interfaces. L'échec est silencieux côté nym. `<OLD-NETNS>` ne redémarre jamais seul. `nym` et `<OLD-NODE-EXIT-NYMVPN>` peuvent donc être recréés séparément.

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

Le `eth0` du schéma est celui du conteneur, en `<DOCKER-INTERNAL-IP>`. L'`eth0` de l'hôte est l'adaptateur filaire, en `<LAN-IP-SERVER>`.

Le trafic des appareils arrive sur `tailscale0`. Il n'est pas marqué. La règle `not from all fwmark 0x14d lookup 333` l'envoie dans la table 333. La route par défaut de la table 333 pointe sur `tun0`. Le trafic marqué de Tailscale, `0x80000`, saute cette règle. Il sort par `eth0`, ce qui évite la boucle.

`<OLD-NODE-EXIT-NYMVPN>` utilise le mode noyau, `TS_USERSPACE=false`. En mode espace utilisateur, Tailscale marque ses paquets avec `0x80000`. Le client Nym marque aussi ses propres sockets avec `0x14d`. Les deux marques peuvent se confondre. Le trafic peut alors repartir par la table principale. Le mode noyau évite cette ambiguïté.

### Les fichiers du projet

Le projet compose vit dans `/opt/tailscale-nym`, répertoire root, avec le fichier `.env` des secrets. Les sources sont dans `tailscale-nym/`, à côté de ce fichier.

| Fichier | Rôle |
|---|---|
| `Dockerfile` | Image Debian bookworm, base et tarball Nym épinglés par digest et SHA-256 |
| `Dockerfile.tailscale` | Image Tailscale dérivée, qui force le backend iptables sur nft |
| `nym-entrypoint.sh` | Dbus, polkit, `nym-vpnd`, puis le superviseur de connexion |
| `49-nymvpn.rules` | Règle polkit qui autorise les actions Nym sur le socket local |
| `docker-compose.yaml` | Les trois services, l'espace réseau partagé, les sysctl |
| `.env` | Le fichier de secrets, mode `600`, absent du repo, sur le serveur |
| `etc-nym/nym-vpnd.json` | Configuration Nym générée et persistée, sur le serveur, hors repo |
| `loop.sh` | Le test de relais entre les deux voies, exécuté sur le Mac |
| `test-client.sh` | Le lancement du conteneur de test `ts-client` sur le Mac |
| `.env.example` | Le gabarit des variables, versionné dans le repo |

Il n'existe pas d'image Nym officielle pour Linux. L'image est construite localement à partir de Debian bookworm, car le client officiel ne fournit que des paquets macOS. La version `2026.12.4` est la dernière qui livre des binaires Linux. Le tarball est vérifié par SHA-256 avant extraction.

### Le superviseur de connexion

`nym-vpnd` ne rétablit pas le tunnel tout seul après un redémarrage. Le superviseur, dans l'entrypoint, garde la connexion. Il lance `nym-vpnd` en arrière-plan, puis boucle toutes les 30 secondes. Il appelle `nym-vpnc connect` tant que l'état n'est pas `Connected`. Il attend pendant les états transitoires. Il n'abandonne jamais. Il relaie `SIGTERM` et `SIGINT` vers `nym-vpnd`, pour que l'arrêt du conteneur reste propre.

Un test a validé ce choix. Après un `nym-vpnc disconnect` manuel, le superviseur a rétabli le tunnel en moins de 12 secondes. Il a gardé les mêmes passerelles.

Le service `<OLD-NODE-EXIT-NYMVPN>` démarre quoi qu'il arrive. Si le tunnel Nym manque, `<OLD-NODE-EXIT-NYMVPN>` est annoncé sans route par défaut. Le trafic est alors perdu au lieu de fuir.

## Le routage mesuré

Ce relevé vient de l'espace réseau du conteneur, tunnel connecté. Les numéros bougent à chaque connexion parce que Nym décale ses règles. L'ordre, lui, ne change pas.

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

Quatre blocs se lisent de haut en bas. Le superviseur place la règle de retour, puis sa règle d'accès direct. Nym place ses deux règles. Tailscale place les siennes. Le superviseur lit la priorité réelle de Nym. Il prend une priorité plus basse, donc ses règles passent avant celles de Nym. L'ordre tient même quand Nym se décale.

La table 52 ne contient que des routes vers les pairs. Elle ne contient aucune route de rejet `0.0.0.0/1`. Un client qui demande une adresse publique ne trouve donc rien dans la table 52. Son trafic retombe sur la règle `not from all fwmark 0x14d lookup 333`, donc dans le tunnel. Ce comportement est voulu. Vérifiez-le après chaque mise à jour de Tailscale. Une route de rejet dans la table 52 noierait tout le trafic sans message d'erreur.

La règle `to 100.64.0.0/10 lookup 52` renvoie au client la réponse qui arrive du tunnel. Elle passe avant toutes les autres.

La règle `fwmark 0x80000/0xff0000 lookup 1000` envoie le trafic propre de Tailscale par `eth0`, hors du tunnel. Sans elle, Nym capturerait ce trafic. Il passerait par le mixnet. Le mixnet coupe la connexion de contrôle au bout de deux minutes.

La règle `not from all fwmark 0x14d lookup 333` appartient à Nym. Elle envoie dans la table 333 tout le trafic qui ne porte pas la marque de Nym.

La règle `from all lookup main suppress_prefixlength 0` masque la route par défaut de la table principale. Le trafic non marqué ne peut donc pas atteindre `eth0` par la route par défaut. Si le tunnel tombe, le trafic est perdu au lieu de repartir en direct. Ce comportement fail-closed est voulu. Vérifiez-le avec `ip route get 8.8.8.8` dans le conteneur. La réponse doit mentionner `tun0` et la table 333.

`tailscaled` utilise deux marques distinctes. Il faut les connaître pour raisonner. Son propre trafic porte `0x80000`. Cette marque couvre le contrôle, les relais DERP et les échanges WireGuard entre pairs. La règle du superviseur l'envoie en direct par `eth0`. Le trafic relayé des clients porte `0x40000`. Cette marque ne vaut pas `0x80000`, donc la règle `fwmark 0x80000/0xff0000` ne la prend pas. Le trafic des clients échappe donc à la règle du superviseur. Il suit le chemin normal. La règle 5270 ne trouve rien dans la table 52 pour une adresse publique. La règle de Nym l'envoie ensuite dans la table 333. Vérifiez ce chemin après toute mise à jour de Tailscale avec `ip route get 9.9.9.9 from <TAILNET-IP-EXIT-NYMVPN> mark 0x40000`. La réponse doit mentionner `tun0` et la table 333.

Le superviseur pose deux règles. Nym installe ses règles juste avant celles de Tailscale. Il les décale à chaque connexion. Une priorité fixe ne tiendrait donc pas. Le superviseur lit la priorité réelle de Nym, puis il prend les priorités `n-1` et `n-2`. Une priorité plus basse est évaluée en premier. Il range la route directe dans la table 1000 :

```
ip rule add priority <n-1> fwmark 0x80000/0xff0000 lookup 1000
```

Le trafic marqué sort alors par `oif "eth0"`. La chaîne `output` de Nym accepte ce chemin. Aucun bistouri n'est nécessaire sur le pare-feu de Nym. Le superviseur repose la règle quand elle manque, parce que Nym reconstruit ses chaînes et ses règles.

La seconde règle renvoie vers `tailscale0` la réponse qui arrive du tunnel à destination d'un client :

```
ip rule add priority <n-2> to 100.64.0.0/10 lookup 52
```

Sans cette règle, la réponse suit la règle de Nym et repart dans le tunnel.

Une conséquence reste à connaître. Le trafic de contrôle de Tailscale, les relais DERP et les échanges WireGuard entre pairs restent en direct par `eth0`, hors du tunnel. C'est nécessaire. Seul le trafic relayé des clients passe par Nym. Le fail-closed porte donc sur les clients, pas sur le contrôle.

## Le pare-feu Nym

Nym installe une table `inet nym` avec `policy drop` sur les chaînes `input`, `output` et `forward`. Les chaînes `output` et `forward` rejettent le port 53 :

```
chain output  { policy drop; udp dport 53 reject; tcp dport 53 reject with tcp reset; reject; }
chain forward { policy drop; udp dport 53 reject; tcp dport 53 reject with tcp reset; reject; }
```

Ce bloc montre seulement le rejet de fin. La chaîne accepte aussi `oif "tun0"` et les passerelles de Nym.

Le résolveur interne de Nym répond. Le port 53 vers l'extérieur est refusé par le noyau. Le noyau renvoie une erreur à l'appelant. N'attendez pas d'absence de réponse. Une absence de réponse signifierait un blocage silencieux.

La table porte aussi une chaîne `nat`, accrochée à `postrouting`. Cette chaîne reste vide. Le relais n'a pas besoin de masquerade. La passerelle de sortie Nym fait le NAT du trafic. La règle de retour `to 100.64.0.0/10 lookup 52` ramène la réponse vers `tailscale0`. Une version antérieure du superviseur écrivait dans `postrouting`. Cette chaîne n'existe pas. L'écriture échouait en silence et le journal annonçait un succès. Ce bloc a été retiré le 2026-10-03.

Au démarrage, Nym tente de réécrire `src_valid_mark` et `arp_ignore` dans `/proc/sys`. Le système de fichiers est en lecture seule. Nym journalise donc `Failed to apply ...: Read-only file system`. Les valeurs sont déjà posées par les `sysctls` du service `netns`. Ces erreurs sont bénignes. Ne les traitez pas comme une panne.

## Le gabarit de la phase C

Chaque service suit le même gabarit. Un `tailscaled` en conteneur compagnon donne au service une adresse Tailscale. Le service pointe ensuite vers `<OLD-SERVER-NAME>` pour un accès direct. Il peut pointer vers `<OLD-NODE-EXIT-NYMVPN>` pour un accès anonymisé, ou vers `none` pour un accès sans exit node.

Démarrez le `tailscaled` avec `--accept-routes=true`. Sans ce drapeau, le nœud ignore la route de l'exit node. La bascule reste sans effet.

Définissez le résolveur DNS du service sur `100.100.100.100`. Sinon, les requêtes de noms de domaine partent vers la `<ISP-BOX>`. Elles quittent le tailnet.

Épinglez l'image par digest. Ajoutez `restart: unless-stopped`. Placez le projet dans `/opt/<service>`, avec le répertoire appartenant à root. Pour changer la sortie en cours d'exécution, lisez `operations.md`.

## Le vocabulaire

Ce glossaire définit les termes du projet. Chaque terme est défini une seule fois dans tout le projet. Le même mot a toujours le même sens.

| Terme | Définition |
|---|---|
| Serveur | Le laptop `<SERVER-MODEL>` sous Alpine. Docker y empile les conteneurs. |
| Conteneur | Un petit système avec ses propres fichiers. Il est isolé des autres conteneurs. |
| Espace réseau | Une pièce isolée avec sa propre table de routage. Un programme qui y tourne sort par la porte de cette pièce. `network_mode: service:X` place un conteneur dans celle de X. Un conteneur qui la partage sort par la même porte. |
| Exit node | Un nœud qui relaie le trafic des autres appareils vers Internet. La sortie de `<OLD-SERVER-NAME>` passe par la `<ISP-BOX>`. La sortie de `<OLD-NODE-EXIT-NYMVPN>` passe par Nym en mode fast. |
| Tailnet | Un réseau privé créé par Tailscale. Chaque nœud a une adresse qui commence par `100.`. Le tailnet de ce projet s'appelle Bonnet2B1. |
| Table de routage | Une liste qui associe chaque destination à une porte. Une entrée `default dev tun0` envoie tout le trafic non étiqueté dans un tunnel. |
| Étiquette de paquet, `fwmark` | Une marque appliquée à un paquet. Un anonymiseur peut étiqueter son propre trafic pour qu'il n'entre pas dans son tunnel. |
| Route par défaut | Une règle de secours qui envoie tout le trafic non prévu vers une seule porte. Une route par défaut pointée sur un tunnel coupe toute fuite. |
| Conteneur compagnon, sidecar | Un conteneur qui fournit un service à un autre conteneur. Ici, `tailscaled` accompagne l'application. |
| `--accept-routes=true` | Le drapeau qui autorise un nœud à suivre la route d'un exit node. |
| DERP | Le relais de secours de Tailscale. Il utilise HTTPS sur le port 443. Tailscale l'emploie quand la connexion directe entre deux nœuds est bloquée. |
| MTU | La taille maximale d'un paquet. Deux tunnels empilés imposent une valeur plus petite que celle du tunnel extérieur. |
| Anonymiseur | Un service qui relaie le trafic vers Internet en cachant l'adresse d'origine. L'anonymiseur de la voie 2 est Nym, en mode fast. |
| SOCKS5 | Un proxy par application. Ce protocole transporte TCP seulement, sans UDP. Un exit node ne l'utilise pas. |
| Mode fast | Un trajet en deux sauts, une passerelle d'entrée puis une passerelle de sortie. L'adresse de sortie visible change selon la passerelle sélectionnée. |
| `.env` | Le fichier de secrets lu par compose. Le fichier reste absent du repo. Le fichier `.env.example` sert de gabarit. |
| Full-tunnel | Une configuration où tout le trafic non étiqueté passe par le tunnel. |
| `<ISP-BOX>` | La box du fournisseur d'accès. Elle est la passerelle du réseau local, `<LAN-GATEWAY-IP>`, et elle porte l'adresse publique de la voie 1. |
| WoL | Le réveil d'un ordinateur à distance, envoyé par le réseau local. |
| MagicDNS | Le résolveur de Tailscale. Il répond en `100.100.100.100` et il résout les noms des nœuds du tailnet. |
| fail-closed | Le comportement d'un tunnel qui perd le trafic au lieu de le laisser partir en direct. |
| supervise-daemon | Le superviseur de services d'OpenRC. Il relance un service qui s'arrête. |
