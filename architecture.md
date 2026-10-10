# Architecture : l'état présent du serveur

```
                        ┌──────────────┐
                        │   INTERNET   │
                        └──────▲───────┘
                ┌──────────────┴───────────────┐
                │                              │
           Sortie <ISP-BOX>               Mode fast, deux sauts
                ▲                              ▲
                │                              │
 ┌──────────────┴──────────────────────────────┴────────────────┐
 │ NIVEAU 2 : LES SORTIES INTERNET                              │
 │                                                              │
 │ ┌────────────────────────┐   ┌─────────────────────────────┐ │
 │ │ VOIE 1 : DIRECTE       │   │ VOIE 2 : ANONYMISÉE         │ │
 │ │ <OLD-SERVER-NAME> / tailscale       │   │ <OLD-NETNS> (espace partagé) │ │
 │ │ réseau de l'hôte       │   │                             │ │
 │ │                        │   │  ┌──────┐ ┌────────────┐    │ │
 │ └────────────▲───────────┘   │  │ nym  │ │ <OLD-NODE-EXIT-NYMVPN>   │    │ │
 │              │               │  │ tun0 │ │ tailscale0 │    │ │
 │              │               │  └──────┘ └────────────┘    │ │
 │              │               │                             │ │
 │              │               └──────────────▲──────────────┘ │
 └──────────────┼──────────────────────────────┼────────────────┘
                │                              │
                └──────────────┬───────────────┘
                               │ choix dans l'application tailscale
                ┌──────────────┴────────────────┐
                │ TAILNET Bonnet2B1             │
                │ iPhone <HOST-IPHONE>               │
                │ MacBook <HOST-MACBOOK>              │
                └───────────────────────────────┘

 ┌──────────────────────────────────────────────────────────────┐
 │ NIVEAU 1 : LE SOCLE COMMUN AUX DEUX VOIES                    │
 │ <SERVER-MODEL> / Alpine / Docker / SSH                          │
 │ eth0 : réseau principal / wlan0 : repli / uplink-guard       │
 └──────────────────────────────────────────────────────────────┘

 ┌──────────────────────────────────────────────────────────────┐
 │ NIVEAU 3 : APPLICATIONS HÉBERGÉES, AUCUN SERVICE DÉPLOYÉ     │
 └──────────────────────────────────────────────────────────────┘

```

Le schéma présente les chemins logiques du trafic et le socle qui les héberge. Les deux voies partagent le laptop et sa liaison réseau. Chaque appareil du tailnet choisit sa voie dans l'application Tailscale.

## Niveau 1 : le socle

Le socle héberge les services de sortie et fournit l'accès au serveur. Il réunit le système, Docker, le réseau local et SSH. Tous les conteneurs utilisent les ressources du même laptop.

### Le système : Alpine

Le serveur est le laptop `<SERVER-MODEL>`, dont le nom d'hôte est `<OLD-SERVER-NAME>`. Il utilise Alpine 3.24 et OpenRC. Le compte d'administration est `<ADMIN-ACCOUNT>`, avec `doas` pour les droits root.

### Les conteneurs : Docker

Docker 29.5.x héberge les services, regroupés en projets Compose v5.1.4. Le projet `/opt/tailscale` porte la voie directe. Le projet `/opt/tailscale-nym` porte la voie anonymisée.

Docker démarre avec le système. Les conteneurs portent une politique de redémarrage automatique. Les volumes conservent les identités Tailscale et les données Nym entre les recréations.

Le redémarrage complet de la configuration réseau actuelle reste non vérifié. Les conteneurs partagent le même hôte. La séparation des deux voies porte sur leurs espaces réseau.

### Le réseau local et uplink-guard

L'adaptateur Ethernet porte `eth0`, en `<LAN-IP-SERVER>`, et négocie 1 Gbit/s. La route principale utilise cette interface avec un metric de 202. La `<ISP-BOX>` est la passerelle du réseau local, en `<LAN-GATEWAY-IP>`.

Le Wi-Fi porte `wlan0`, en `<LAN-IP-WIFI>/24`, avec un metric de 303. Il reste associé pendant l'utilisation d'Ethernet. Il fournit le repli lorsque le lien filaire manque.

`uplink-guard` épingle la route vers la passerelle sur `eth0` lorsque le lien filaire est disponible. Il retire cet épinglage lorsque le lien manque. Le Wi-Fi reprend alors le trafic. OpenRC supervise le gardien au runlevel `default`.

La configuration des interfaces vit dans `/etc/network/interfaces`. Le programme du gardien est `/usr/local/bin/uplink-guard`. Son service OpenRC est `/etc/init.d/uplink-guard`.

### L'accès au serveur : SSH

SSH donne accès au compte `<ADMIN-ACCOUNT>` par l'adresse Tailscale `<TAILNET-IP-EXIT-DIRECT>`. Le service écoute sur `0.0.0.0:22`. Sa configuration vit dans `/etc/ssh/sshd_config`.

L'authentification utilise une clé seule. `PasswordAuthentication` vaut `no`. La connexion root est désactivée.

## Niveau 2 : les sorties Internet

Le tailnet Bonnet2B1 contient deux exit nodes, `<OLD-SERVER-NAME>` et `<OLD-NODE-EXIT-NYMVPN>`. L'iPhone `<HOST-IPHONE>` et le MacBook `<HOST-MACBOOK>` utilisent ces sorties. Les nœuds ont des adresses Tailscale et des espaces réseau distincts.

### La sortie directe : tailscale / `<OLD-SERVER-NAME>`

Le conteneur `tailscale` porte le nœud `<OLD-SERVER-NAME>`, en `<TAILNET-IP-EXIT-DIRECT>`. Il utilise le réseau de l'hôte et sort par la `<ISP-BOX>`. L'adresse publique de cette sortie est dynamique.

Le projet compose vit dans `/opt/tailscale` et utilise l'image officielle Tailscale. Ses sources sont versées dans [docker-compose.yaml](tailscale/docker-compose.yaml). Le conteneur dispose des capacités `NET_ADMIN` et `NET_RAW`, ainsi que de `/dev/net/tun`. `tailscaled` démarre avec l'option `--tun=userspace-networking`. Le nœud tourne en mode espace utilisateur et n'installe aucune règle de pare-feu sur l'hôte. Le serveur ne porte aucune interface `tailscale0`. Le conteneur ne voit pas le tunnel de la voie anonymisée.

L'état du nœud vit dans le volume `state`, au chemin `/var/lib/tailscale`. Ce volume conserve son identité entre les redémarrages et les recréations. `<OLD-SERVER-NAME>` est approuvé comme exit node dans la console Tailscale.

### L'espace réseau de la voie anonymisée : `<OLD-NETNS>`

Le conteneur `<OLD-NETNS>` porte l'espace réseau de la voie anonymisée. Les conteneurs `nym` et `<OLD-NODE-EXIT-NYMVPN>` rejoignent cet espace. Ils partagent ses interfaces, ses tables de routage et ses règles nft.

L'interface `eth0` de cet espace porte `<DOCKER-INTERNAL-IP>` sur le réseau Docker. `tun0` donne accès au tunnel Nym. `tailscale0` donne accès aux appareils du tailnet. L'`eth0` de l'hôte reste une interface distincte.

Le service `netns` pose les paramètres réseau partagés, dont `src_valid_mark` et `arp_ignore`. Sa définition est dans [docker-compose.yaml](tailscale-nym/docker-compose.yaml). Ce fichier définit aussi les deux services qui partagent l'espace.

### Le tunnel : nym

Le conteneur `nym` fournit le tunnel Nym en mode fast. Le trafic traverse deux passerelles avant sa sortie Internet. L'adresse publique de sortie change avec les passerelles sélectionnées.

Son image `local/nym-vpn-client:2026.12.4` utilise les binaires Linux Nym sur Debian bookworm. Le [Dockerfile](tailscale-nym/Dockerfile) décrit sa construction. La base et le tarball sont épinglés, et le tarball est vérifié par SHA-256.

Le fichier [nym-entrypoint.sh](tailscale-nym/nym-entrypoint.sh) lance Dbus, polkit et `nym-vpnd`, puis supervise la connexion. La règle [49-nymvpn.rules](tailscale-nym/49-nymvpn.rules) autorise les actions Nym sur le socket local. La configuration persistante vit dans `etc-nym/nym-vpnd.json` sur le serveur.

Les données Nym vivent dans le volume `nym-data`, monté dans `/var/lib/nym-vpnd`. La graine Nym est stockée dans `mainnet/mnemonic.json`, à l'intérieur de ce volume. Ce stockage est distinct de la configuration `etc-nym/nym-vpnd.json`.

#### Le superviseur de connexion

Le superviseur est une boucle dans l'entrypoint du conteneur `nym`. Il lance `nym-vpnd` en arrière-plan, puis boucle toutes les 30 secondes. Il demande la connexion tant que l'état n'est pas `Connected`.

Il attend pendant les états transitoires et continue les tentatives de connexion. L'état stable `Disconnected` compte comme un échec, pas comme une transition. Il déclenche une tentative. Le superviseur rétablit les règles de routage et de pare-feu nécessaires au relais. Il relaie `SIGTERM` et `SIGINT` vers `nym-vpnd`.

#### Le pare-feu Nym

Nym installe une table `inet nym` avec une politique de rejet sur les chaînes `input`, `output` et `forward`. Le superviseur ajoute les autorisations nécessaires au contrôle Tailscale et au relais des clients. Les chemins du tunnel et des passerelles Nym sont autorisés.

Le résolveur interne de Nym répond. Nym refuse le port 53 vers l'extérieur par ses règles nft. Seuls ses propres résolveurs sont autorisés dans le tunnel. L'appelant reçoit une erreur.

La table porte une chaîne `nat`, accrochée à `postrouting`. Cette chaîne reste vide. Aucune chaîne nommée `postrouting` n'existe dans la table `inet nym`. La passerelle de sortie Nym fait le NAT du trafic relayé. Les réponses au tailnet suivent la règle de retour vers la table 52.

### La sortie anonymisée : `<OLD-NODE-EXIT-NYMVPN>`

Le conteneur `<OLD-NODE-EXIT-NYMVPN>` porte le nœud Tailscale du même nom, en `<TAILNET-IP-EXIT-NYMVPN>`. Il utilise le mode noyau de Tailscale et l'espace réseau tenu par `<OLD-NETNS>`. Il est approuvé comme exit node dans la console Tailscale.

L'image `local/tailscale-nft:1.102.5` utilise le backend nft d'iptables. Sa construction est décrite dans [Dockerfile.tailscale](tailscale-nym/Dockerfile.tailscale). Le volume `state` conserve l'identité du nœud.

Le projet partagé vit dans `/opt/tailscale-nym`. Son fichier `.env` reste sur le serveur. Le fichier [.env.example](tailscale-nym/.env.example) décrit les variables du projet.

#### Le routage

Les règles de routage distinguent les réponses au tailnet, le trafic propre de Tailscale et le trafic relayé des clients. Leurs priorités changent avec les connexions Nym. Le superviseur lit la priorité réelle de Nym et place ses règles avant elle.

La priorité `n` est la plus basse des deux priorités Nym. La règle de retour du superviseur prend `n-2`. Sa règle directe prend `n-1`. Une priorité plus basse est évaluée en premier. Les règles du superviseur précèdent donc celles de Nym, qui précèdent celles de Tailscale.

La règle de retour dirige les destinations `100.64.0.0/10` vers la table 52. Cette table porte les routes vers les pairs du tailnet par `tailscale0`. Elle ne contient pas de route de rejet `0.0.0.0/1`. Le superviseur lit le numéro de la table dans les règles de Tailscale.

Le trafic propre de Tailscale porte la marque `0x80000`. Cette marque couvre le contrôle, les relais DERP et les échanges WireGuard entre pairs. La règle directe du superviseur sélectionne cette marque avec le masque `0xff0000` et utilise la table 1000. Cette table sort par l'`eth0` de l'espace réseau `<OLD-NETNS>`, hors du tunnel. Le paquet traverse ensuite le pont Docker, puis l'`eth0` de l'hôte.

Le superviseur marque le trafic relayé des clients avec `0x40000` dans le pare-feu. Cette marque échappe à la règle directe qui sélectionne `0x80000`. Pour une destination publique, la règle Nym dirige le trafic vers la table 333. La route par défaut de cette table utilise `tun0`. Elle porte une MTU de 1340 octets. Un paquet plus grand est jeté par le tunnel.

Une règle Nym masque la route par défaut de la table principale. Le trafic relayé des clients ne dispose donc pas de repli direct par `eth0`. Le fail-closed concerne ce trafic. Le contrôle Tailscale reste en direct.
