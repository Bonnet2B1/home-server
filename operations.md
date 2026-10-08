# Operations : les procédures

Ce fichier donne les commandes à exécuter. Avant d'exécuter, lisez `guidelines.md`. Certaines commandes de ce fichier sont interdites ailleurs.

## La connexion

Par le tailnet, connectez-vous avec cette commande :

```sh
ssh <ADMIN-ACCOUNT>@<TAILNET-IP-EXIT-DIRECT>
```

L'adresse `<LAN-IP-WIFI>` est l'adresse du réseau local. Elle fonctionne depuis une machine sur place. Depuis un Mac connecté au tailnet, elle échoue. Le trafic du Mac est routé par erreur dans un tunnel local. Préférez l'adresse du tailnet.

## La mise en place de la voie 2

Si vous lancez `docker compose up -d` sans argument après un build, Compose recréerait `<OLD-NETNS>`. Son image est partagée avec `nym`. L'espace réseau serait perdu. Utilisez `--no-deps`, qui ne recrée que `nym`.

Copiez les sources du dépôt vers le serveur, à la main, avec `scp` ou `rsync`.

Ces commandes s'exécutent sur `<OLD-SERVER-NAME>`, avec `doas` :

```sh
cd /opt/tailscale-nym
doas docker compose build nym
doas docker compose up -d --no-deps nym
```

Si la pile est arrêtée, lancez `doas docker compose up -d` une fois. Relisez ensuite l'identifiant de l'espace avec cette commande :

```sh
doas docker inspect -f '{{.NetworkSettings.SandboxKey}}' <OLD-NETNS>
```

## L'état de la voie 2

Ces commandes donnent l'état du tunnel et l'état du routage :

```sh
doas docker exec nym nym-vpnc status --table-style blank
doas docker exec nym sh -c 'curl -s --max-time 20 https://api.ipify.org; echo'
doas docker exec nym ip rule
doas docker exec nym ip route show table 333
doas docker logs nym | grep superviseur
```

Ne lancez jamais `nym-vpnd -v`. La règle et sa raison sont dans `guidelines.md`. Pour raisonner sur le routage, lisez « Le routage mesuré » dans `architecture.md`.

## La sortie d'un microservice

Pour changer la sortie d'un service pendant son exécution, lancez une de ces trois commandes :

```sh
doas docker exec <service> tailscale set --exit-node=<OLD-NODE-EXIT-NYMVPN>   # anonymisé
doas docker exec <service> tailscale set --exit-node=<OLD-SERVER-NAME>       # direct, plein débit
doas docker exec <service> tailscale set --exit-node=none       # pas d'exit node
```

Vérifiez la sortie active avec `doas docker exec <service> tailscale status`. La console Tailscale affiche aussi la sortie de chaque nœud. Vous pouvez créer un alias court pour chaque service.

## Le redémarrage de l'hôte

Un `doas reboot` ne change rien aux deux voies. Les conteneurs remontent seuls parce qu'ils portent `restart: unless-stopped`. Le résultat du test du 2026-10-03 est dans `runbook.md`, section « Le redémarrage de l'hôte, testé le 2026-10-03 ».

Attendez une minute après le reboot, puis lancez ces commandes :

```sh
doas docker ps -a --format '{{.Names}} {{.Status}}'
doas docker exec <OLD-NODE-EXIT-NYMVPN> tailscale ip -4
doas docker logs nym | grep superviseur
```

Attendu : les quatre conteneurs sont `Up`. `<OLD-SERVER-NAME>` garde `<TAILNET-IP-EXIT-DIRECT>`. `<OLD-NODE-EXIT-NYMVPN>` garde `<TAILNET-IP-EXIT-NYMVPN>`. Le superviseur journalise la reconnexion du tunnel Nym.

## La maintenance

Mettez à jour le système volontairement. N'utilisez jamais `latest` sans vérification.

Pour Alpine et Docker, faites une mise à jour chaque trimestre. Faites aussi une mise à jour après un correctif de sécurité important :

```sh
doas apk update && doas apk upgrade
```

Redémarrez le serveur si le noyau a changé. Le module `tun` se recharge au boot. Docker redémarre avec lui.

Pour `<OLD-SERVER-NAME>`, changez l'image par digest dans `/opt/tailscale`. Lancez `doas docker compose pull`, puis `doas docker compose up -d --force-recreate`. L'état du nœud reste dans le volume `state`.

Pour `<OLD-NODE-EXIT-NYMVPN>`, l'image Nym est construite localement. Après une modification des sources dans le dépôt, copiez-les sur le serveur, puis lancez `doas docker compose build nym` dans `/opt/tailscale-nym`. Puis lancez `doas docker compose up -d --no-deps nym`. Ne recréez pas `<OLD-NETNS>` seul, car son espace réseau héberge `nym` et `<OLD-NODE-EXIT-NYMVPN>`.

Les clients du tailnet se mettent à jour depuis l'App Store ou le magasin d'applications. Aucune action n'est nécessaire sur le serveur. N'écrivez pas de script unique avant d'avoir assez de projets.

## Le nettoyage

Une session de travail peut perdre la mémoire. Cette section permet à une personne qui n'a rien vécu de nettoyer la machine. Elle part de cette documentation seule.

### Le diagnostic de la voie 2 sur le Mac

Colima et Docker servaient de client Tailscale de test sur le Mac. Ils ne touchaient pas le Mac lui-même. Pour les retirer, lancez ces commandes :

```sh
docker rm -f ts-client
colima stop
colima delete          # supprime la machine virtuelle et ses volumes
brew uninstall colima docker lima
```

Le conteneur de test `ts-client` utilise l'image `tailscale/tailscale:stable`. Depuis le 2026-10-03, cette image est basée sur Alpine 3.22.6. Elle ne contient ni `curl` ni `dig`, dont `loop.sh` a besoin. Depuis la même date, `loop.sh` installe les deux outils lui-même. Il vérifie la présence du conteneur `ts-client`, puis il lance `apk add --no-cache curl bind-tools`. Si cette installation automatique échoue, gardez la commande manuelle :

```sh
docker exec ts-client apk add --no-cache curl bind-tools
```

### Le nœud de test

Le nœud `ts-test` du tailnet se supprime depuis la console Tailscale. Une clé `ephemeral` le ferait disparaître seul. Celle du 2026-10-03 n'était pas éphémère. Le nœud s'appelle donc `ts-test-1`, parce que `ts-test` existait déjà.

### Les règles nft temporaires

Les deux règles nft temporaires commentées `TEMPO` ont disparu avec les recréations du conteneur `nym`. Vérifiez qu'il n'en reste aucune avec cette commande. La commande ne doit renvoyer aucune règle `TEMPO`.

```sh
doas docker exec nym nft list chain inet nym forward
```

### Les clés à révoquer

Ces clés ont servi au diagnostic ou à l'enregistrement. Elles ne servent plus. Révoquez-les dans la console Tailscale, section des clés.

- La clé de `/opt/tailscale/.env`, consommée le 2026-10-03. Une clé est à usage unique. L'identité du nœud vit dans le volume `state`, donc la clé n'est plus nécessaire. Elle a été retirée du fichier `.env` et de `docker-compose.yaml` le 2026-10-03.
- La clé de `/opt/tailscale-nym/.env`, utilisée pour `<OLD-NODE-EXIT-NYMVPN>`.
- La clé du conteneur de test `ts-client` sur le Mac, celle qui a créé `ts-test-1`.
- Les clés plus anciennes visibles dans l'historique du shell, `/home/<ADMIN-ACCOUNT>/.ash_history`, notamment celles des lignes 58 et 263.

Le secret `TS_AUTHKEY` de la voie 2 apparaît en clair dans `docker inspect <OLD-NODE-EXIT-NYMVPN>`. C'est normal. La variable est passée par l'environnement du conteneur. Le conteneur `tailscale` de la voie 1 ne porte plus de clé depuis le 2026-10-03. Les fichiers `.env` restent en mode `600`.
