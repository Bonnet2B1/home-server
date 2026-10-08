# Maintenance : les procédures

Ce fichier rassemble les procédures d'entretien, de diagnostic et de réparation du serveur. Les commandes serveur utilisent le compte `<ADMIN-ACCOUNT>`. Les commandes Mac concernent le client de diagnostic.

## La connexion

L'accès distant utilise l'adresse Tailscale `<TAILNET-IP-EXIT-DIRECT>`. Le compte d'administration est `<ADMIN-ACCOUNT>`. Les règles d'intervention sont dans [guidelines.md](guidelines.md), section « Le travail ».

Depuis un appareil connecté au tailnet, ouvrez la session SSH :

```sh
ssh <ADMIN-ACCOUNT>@<TAILNET-IP-EXIT-DIRECT>
```

Le résultat attendu est une session sur `<OLD-SERVER-NAME>`, avec le compte `<ADMIN-ACCOUNT>`. Les commandes Docker du serveur utilisent `doas`. Cette connexion ne dépend pas du tunnel Nym. Elle exige que le poste client ait sélectionné `<OLD-SERVER-NAME>`.

## Le diagnostic de la voie directe

Ces contrôles nécessitent un accès au serveur, par le réseau local ou sur place. Ils vérifient le conteneur Tailscale et la connectivité de l'hôte. La décision sur une modification du DNS reste dans [todo.md](todo.md), section « Le DNS de l'hôte lors d'une récupération ».

Sur le serveur, relevez l'état du conteneur :

```sh
doas docker ps -a --format '{{.Names}} {{.Status}}'
doas docker inspect -f '{{.State.Status}} {{.State.ExitCode}}' tailscale
```

Le conteneur attendu est `tailscale`, à l'état `running`. Un état arrêté ou des redémarrages répétés indiquent un échec de démarrage. Le code de sortie complète ce constat.

Vérifiez que l'identité du nœud est persistée :

```sh
doas docker exec tailscale ls -l /var/lib/tailscale/tailscaled.state
```

Le fichier `tailscaled.state` doit exister dans le conteneur. Son absence indique une identité en mémoire, perdue à chaque recréation.

Relevez uniquement les motifs d'erreur suivants dans le journal :

```sh
doas docker logs --tail 80 tailscale 2>&1 | grep -oE 'NeedsLogin|network is unreachable|no such host|panic'
```

`NeedsLogin` indique un besoin d'enregistrement. Les deux erreurs réseau concernent la connectivité ou la résolution de noms. `panic` indique un arrêt anormal. Une sortie vide signifie seulement que ces motifs sont absents des lignes examinées.

Vérifiez la route, les résolveurs et l'accès à une adresse publique :

```sh
ip -4 route
grep -E '^[[:space:]]*nameserver[[:space:]]+' /etc/resolv.conf
doas ping -c 2 1.1.1.1
```

La route par défaut doit utiliser une liaison disponible et la passerelle `<LAN-GATEWAY-IP>`. Les lignes `nameserver` identifient les résolveurs configurés. Le ping doit recevoir des réponses. Ces lectures ne suffisent pas à justifier un changement de DNS.

## L'état de la voie 2

Le conteneur `nym` fournit le tunnel. Le conteneur `<OLD-NODE-EXIT-NYMVPN>` fournit le nœud Tailscale. Les deux partagent l'espace réseau de `<OLD-NETNS>`.

Ne lancez jamais `nym-vpnd -v`. Ce mode affiche la graine Nym dans les journaux. Les règles de protection des secrets sont dans [guidelines.md](guidelines.md), section « Les secrets ».

Sur le serveur, relevez l'état du tunnel, du nœud et de la sortie :

```sh
doas docker exec nym nym-vpnc status --table-style blank
doas docker exec <OLD-NODE-EXIT-NYMVPN> tailscale status
doas docker exec nym curl -s --max-time 20 https://api.ipify.org
doas docker logs nym 2>&1 | grep -F '[superviseur]'
```

Le tunnel doit afficher `Connected`. Le nœud doit apparaître dans le tailnet sans avertissement de santé. La requête HTTP doit renvoyer une adresse publique. La comparaison avec la sortie directe suit la section « La vérification des sorties ».

## La vérification des sorties

Cette vérification compare la sortie directe et la sortie Nym depuis l'iPhone. L'adresse publique de la `<ISP-BOX>` peut changer. Le témoin direct se mesure pendant la même vérification.

Depuis l'iPhone, sélectionnez `<OLD-SERVER-NAME>` dans l'application Tailscale. Ouvrez `https://api.ipify.org`. Notez l'adresse affichée comme témoin direct.

Sélectionnez ensuite `<OLD-NODE-EXIT-NYMVPN>`. Ouvrez la même adresse. Vérifiez que l'adresse affichée diffère du témoin direct.

## La vérification du routage de la voie 2

Ces contrôles s'exécutent sur le serveur, dans l'espace réseau partagé par `nym` et `<OLD-NODE-EXIT-NYMVPN>`. Ils décrivent le routage avec le tunnel connecté. Les règles applicables sont dans [guidelines.md](guidelines.md).

Après une mise à jour de Tailscale, relevez les règles :

```sh
doas docker exec nym ip rule
```

Relevez le numéro de table dans la règle de retour vers `100.64.0.0/10`. Dans les commandes suivantes, remplacez `52` si ce numéro diffère. Vérifiez les tables :

```sh
TABLE_TAILSCALE=52
doas docker exec nym ip route show table "$TABLE_TAILSCALE"
doas docker exec nym ip route show table 333
doas docker exec nym ip route show table 1000
```

La règle de retour vers le tailnet précède la règle directe du superviseur. Les deux précèdent les règles Nym. La table Tailscale porte les routes vers les pairs, sans route de rejet `0.0.0.0/1`. La table 333 pointe sur `tun0`. La table 1000 porte la sortie directe par `eth0`.

Vérifiez le chemin vers une adresse publique avec cette commande :

```sh
doas docker exec nym ip route get 8.8.8.8
```

La réponse attendue mentionne `tun0` et la table 333. Le mécanisme fail-closed est décrit dans [architecture.md](architecture.md), section « Le routage ». Cette lecture vérifie le chemin choisi avec le tunnel connecté.

Vérifiez aussi le chemin du trafic marqué des clients avec cette commande :

```sh
doas docker exec nym ip route get 9.9.9.9 from <TAILNET-IP-EXIT-NYMVPN> mark 0x40000
```

La réponse attendue mentionne `tun0` et la table 333. La marque `0x40000` distingue le trafic relayé des clients. La sortie directe du contrôle Tailscale utilise la marque `0x80000`.

## Le diagnostic DNS et sysctl de Nym

Le résolveur interne de Nym répond, mais le port 53 vers l'extérieur est refusé par le noyau. Le refus produit une erreur pour l'appelant. Une absence de réponse correspond à un blocage silencieux différent.

Au démarrage, Nym tente de réécrire `src_valid_mark` et `arp_ignore` dans `/proc/sys`. Le système de fichiers est en lecture seule. Le journal peut donc afficher `Failed to apply ...: Read-only file system`.

Les valeurs sont déjà posées par les sysctl du service `netns`. Ce message décrit un refus de réécriture. Il ne suffit pas à établir une panne du tunnel.

## Le diagnostic du lien filaire

L'interface filaire du serveur est `eth0`. Le Wi-Fi de repli est `wlan0`. Le gardien `uplink-guard` adapte la route vers la passerelle selon la disponibilité du lien.

Sur le serveur, relevez le lien et les routes :

```sh
doas ethtool eth0
ip -4 addr show dev eth0
ip -4 route
```

Lorsque le câble est connecté, `Link detected` doit valoir `yes`. `eth0` doit porter son adresse IPv4. La route vers la passerelle doit utiliser le lien filaire. Lorsque le lien manque, la route doit permettre le repli Wi-Fi.

## Le client de diagnostic sur le Mac

[test-client.sh](tailscale-nym/test-client.sh) lance le conteneur Tailscale de test `ts-client`. [loop.sh](tailscale-nym/loop.sh) teste le relais entre les deux voies. Les commandes de cette section s'exécutent sur le Mac, dans son contexte Docker de diagnostic.

Vérifiez le contexte Docker et la présence du conteneur :

```sh
docker context show
docker ps -a --filter name=ts-client --format '{{.Names}} {{.Status}}'
```

Le contexte doit correspondre à l'environnement local de diagnostic. Le conteneur attendu est `ts-client`. Un contexte distant ou un conteneur absent demande un diagnostic avant de poursuivre.

Si les outils manquent dans un client Alpine, installez-les dans ce conteneur :

```sh
docker exec ts-client apk add --no-cache curl bind-tools
```

Vérifiez leur disponibilité :

```sh
docker exec ts-client sh -c 'command -v curl && command -v dig'
```

Les deux commandes doivent renvoyer un chemin. La boucle de diagnostic peut alors utiliser `curl` et `dig`. Le nettoyage éventuel de cet environnement est dans [todo.md](todo.md), section « Le nettoyage de l'environnement de diagnostic ».

Lancez le client de test avec la clé d'authentification fournie par l'utilisateur :

```sh
sh tailscale-nym/test-client.sh <clé> <OLD-NODE-EXIT-NYMVPN>
```

Lancez ensuite la boucle de relais :

```sh
bash tailscale-nym/loop.sh
```

La boucle contrôle d'abord `<OLD-SERVER-NAME>`, puis la cible `<OLD-NODE-EXIT-NYMVPN>`. Deux verdicts `VERT` indiquent un relais correct. Un verdict `ROUGE` sur la cible signale un défaut du relais.

## La sortie d'un microservice

Cette procédure concerne un service qui possède un conteneur compagnon Tailscale. Le choix s'applique à ce compagnon. Les trois modes sont une sortie Nym, une sortie directe ou aucun exit node.

Remplacez la valeur suivante par le nom du conteneur compagnon :

```sh
SERVICE_TAILSCALE='nom-du-conteneur-compagnon'
```

Pour la sortie Nym, lancez cette commande sur le serveur :

```sh
doas docker exec "$SERVICE_TAILSCALE" tailscale set --exit-node=<OLD-NODE-EXIT-NYMVPN>
```

Pour la sortie directe, lancez cette commande :

```sh
doas docker exec "$SERVICE_TAILSCALE" tailscale set --exit-node=<OLD-SERVER-NAME>
```

Pour retirer le choix d'un exit node, lancez cette commande :

```sh
doas docker exec "$SERVICE_TAILSCALE" tailscale set --exit-node=none
```

Vérifiez le choix actif :

```sh
doas docker exec "$SERVICE_TAILSCALE" tailscale status
```

Le résultat doit correspondre au nœud sélectionné, ou à l'absence d'exit node. La console Tailscale affiche aussi le choix du service. La vérification de sa sortie Internet complète ce contrôle.

## Le redémarrage de l'hôte

Cette procédure vérifie la reprise des services après un redémarrage. Le test passé est consigné dans [logbook.md](logbook.md), section « Le redémarrage de l'hôte, testé le 2026-10-03 ». La validation de la configuration réseau actuelle reste une tâche dans [todo.md](todo.md).

Après un redémarrage, reconnectez-vous au serveur. Vérifiez les conteneurs, les adresses et le superviseur :

```sh
doas docker ps -a --format '{{.Names}} {{.Status}}'
doas docker exec tailscale tailscale ip -4
doas docker exec <OLD-NODE-EXIT-NYMVPN> tailscale ip -4
doas docker logs nym 2>&1 | grep -F '[superviseur]'
doas rc-status default | grep uplink-guard
ip -4 addr show dev eth0
ip -4 addr show dev wlan0
ip -4 route get <LAN-GATEWAY-IP>
```

Les conteneurs `tailscale`, `<OLD-NETNS>`, `nym` et `<OLD-NODE-EXIT-NYMVPN>` doivent être `Up`. `<OLD-SERVER-NAME>` doit garder `<TAILNET-IP-EXIT-DIRECT>`. `<OLD-NODE-EXIT-NYMVPN>` doit garder `<TAILNET-IP-EXIT-NYMVPN>`. Le superviseur doit journaliser la reconnexion. Le gardien `uplink-guard` doit Started dans le runlevel `default`. `eth0` doit porter `<LAN-IP-SERVER>`. `wlan0` doit garder `<LAN-IP-WIFI>`. La route vers `<LAN-GATEWAY-IP>` doit utiliser `eth0`. La section « La vérification des sorties » vérifie ensuite le relais.

## La mise à jour du système

Cette procédure concerne Alpine et Docker sur le serveur. Docker vient des paquets Alpine, donc `apk upgrade` le met à jour. La cadence retenue est trimestrielle, avec une intervention après un correctif de sécurité important. Un redémarrage du serveur affecte aussi la voie 1. La date de la dernière mise à jour n'est pas consignée.

Avant cette intervention, obtenez l'accord de l'utilisateur. Relevez le noyau chargé et les modules disponibles :

```sh
uname -r
ls /lib/modules
```

Le noyau chargé est `6.18.53-0-lts`. Comparez la liste des modules après la mise à jour. Si elle a changé, le noyau a changé.

Lancez la mise à jour :

```sh
doas apk update && doas apk upgrade
```

Si le noyau a changé, convenez du redémarrage avec l'utilisateur. Vérifiez ensuite les services selon la section « Le redémarrage de l'hôte ». Si le noyau n'a pas changé, ne redémarrez pas. Vérifiez les sorties selon la section « La vérification des sorties ». La mise à jour doit se terminer sans erreur de paquet.

## La mise à jour de la voie directe

Le projet de la voie directe est `/opt/tailscale`. Son identité persistante vit dans le volume `state`. Cette intervention demande l'accord de l'utilisateur.

Après accord, mettez à jour le digest de l'image dans le compose. Sur le serveur, lancez la mise à jour :

```sh
cd /opt/tailscale
doas docker compose pull
doas docker compose up -d --force-recreate
```

Vérifiez le retour de la connexion SSH et l'adresse du nœud :

```sh
doas docker exec tailscale tailscale ip -4
```

Le nœud doit garder `<TAILNET-IP-EXIT-DIRECT>`. Le conteneur doit reprendre sans perdre son identité. La section « La vérification des sorties » vérifie le résultat depuis un client.

## Le transfert des sources de la voie 2

Cette procédure prépare une mise à jour d'un projet existant. Elle transfère les fichiers nécessaires aux images et au compose. Les données persistantes et le fichier `.env` restent sur le serveur.

Dans une session SSH, créez un répertoire temporaire :

```sh
DEPLOY_DIR=$(mktemp -d "$HOME/tailscale-nym-deploy.XXXXXX")
printf '%s\n' "$DEPLOY_DIR"
```

Notez le chemin affiché. Gardez cette session SSH ouverte. Depuis le Mac, remplacez la valeur suivante par ce chemin.

Depuis la racine du dépôt sur le Mac, copiez les sources :

```sh
DEPLOY_DIR='CHEMIN_RELEVE_SUR_LE_SERVEUR'
scp tailscale-nym/Dockerfile \
    tailscale-nym/Dockerfile.tailscale \
    tailscale-nym/nym-entrypoint.sh \
    tailscale-nym/49-nymvpn.rules \
    tailscale-nym/docker-compose.yaml \
    "<ADMIN-ACCOUNT>@<TAILNET-IP-EXIT-DIRECT>:$DEPLOY_DIR/"
```

Dans la session SSH conservée, copiez ces fichiers dans le projet :

```sh
doas cp "$DEPLOY_DIR/Dockerfile" \
    "$DEPLOY_DIR/Dockerfile.tailscale" \
    "$DEPLOY_DIR/nym-entrypoint.sh" \
    "$DEPLOY_DIR/49-nymvpn.rules" \
    "$DEPLOY_DIR/docker-compose.yaml" \
    /opt/tailscale-nym/
```

Les cinq fichiers doivent rejoindre `/opt/tailscale-nym/` sans erreur de copie. Cette étape ne reconstruit pas les images. La procédure suivante applique les changements aux services concernés.

## La reconstruction de la voie 2

Les noms de services Compose sont `netns`, `nym` et `tailscale`. Leurs conteneurs sont `<OLD-NETNS>`, `nym` et `<OLD-NODE-EXIT-NYMVPN>`. Le projet vit dans `/opt/tailscale-nym`.

Si seule l'image ou l'entrypoint Nym change, recréez uniquement `nym` :

```sh
cd /opt/tailscale-nym
doas docker compose build nym
doas docker compose up -d --no-deps nym
```

Le conteneur `<OLD-NETNS>` doit conserver son espace réseau. Le nœud `<OLD-NODE-EXIT-NYMVPN>` doit garder son identité. Le superviseur doit reconnecter le tunnel.

Si l'image Tailscale ou la configuration de l'espace partagé change, reconstruisez et recréez les trois services :

```sh
cd /opt/tailscale-nym
doas docker compose build tailscale
doas docker compose build nym
doas docker compose up -d --force-recreate netns nym tailscale
doas docker inspect -f '{{.NetworkSettings.SandboxKey}}' <OLD-NETNS>
```

L'inspection doit afficher le chemin de l'espace réseau du conteneur recréé. Les volumes conservent les identités et les données Nym. Les sections « L'état de la voie 2 » et « La vérification du routage de la voie 2 » vérifient la reprise.

## La mise à jour des clients

Les applications du tailnet se mettent à jour sur leurs appareils. L'iPhone utilise l'App Store. Les autres appareils utilisent leur magasin d'applications ou leur méthode d'installation.

Après une mise à jour du client, vérifiez les deux sorties avec la section « La vérification des sorties ». Les nœuds doivent rester sélectionnables. Les adresses de sortie doivent correspondre au mode choisi.
