# Todo : les tâches restantes

Ce fichier liste les tâches restantes. Chaque tâche porte son objectif, ses conditions, ses étapes et ses critères de réussite. Le détail des faits est dans [architecture.md](architecture.md) et dans [logbook.md](logbook.md).

## La voie 2

La voie 2 est en service depuis le 2026-10-03. Une seule tâche lui reste ouverte.

### Le géo-bypass et les pays à risque

#### Objectif

Établir une liste sourcée des pays dont les gouvernements menacent la confidentialité des nœuds. Le géo-bypass est activé selon cette liste.

#### Conditions

La liste des pays est sourcée et approuvée. Les données de localisation transmises sont vérifiées avant activation.

#### Étapes

- Ajoutez les pays qui imposent des restrictions excessives au trafic Internet.
- Vérifiez comment le géo-bypass traite ces pays.
- Vérifiez quelles données de localisation il transmet.
- Activez le géo-bypass selon la liste retenue.
- Mettez à jour [philosophy.md](philosophy.md) pour refléter ce choix.

#### Critères de réussite

- Chaque pays de la liste possède une source.
- Les données de localisation transmises sont connues.
- Le géo-bypass suit la liste approuvée.
- [philosophy.md](philosophy.md) reflète le choix retenu.

## Les étapes communes

Ces étapes concernent les deux voies. Elles ne font partie d'aucune phase. Six étapes restent ouvertes.

### Le réglage DNS d'AdGuard Home

#### Objectif

Définir le réglage DNS d'AdGuard Home. Le réglage doit éviter toute boucle de résolution par le tailnet.

#### Conditions

Le déploiement d'AdGuard Home déclenche cet arbitrage. Les sources définissent `TS_ACCEPT_DNS=false` et le gabarit prévoyait `100.100.100.100`.

#### Étapes

- Choisissez un réglage sans boucle DNS.
- Définissez le résolveur amont selon le choix de sortie.
- Vérifiez la compatibilité avec la sortie choisie.
- Vérifiez le fonctionnement DNS avant la fin de la tâche.

#### Critères de réussite

- La résolution par le tailnet ne boucle pas.
- Le réglage est compatible avec la sortie choisie.
- Le fonctionnement DNS est vérifié avant la fin.

### Le DNS de l'hôte lors d'une récupération

#### Objectif

Trancher le choix du DNS de l'hôte lors d'une récupération. La voie 1 donne l'accès distant au serveur. Cette décision concerne le DNS de l'hôte, pas le DNS du futur service AdGuard. L'ancienne procédure proposait un résolveur public si `/etc/resolv.conf` pointait vers `100.100.100.100`. Cette piste a été écartée le 2026-10-03 au profit d'un diagnostic d'identité non persistante.

#### Conditions

Le diagnostic est dans [logbook.md](logbook.md), section « La résolution du 2026-10-03 ». Une récupération de la voie 1 rend ce choix nécessaire.

#### Étapes

- Choisissez entre un diagnostic sans changement de DNS et un recours temporaire à un résolveur public.
- Avant toute modification, vérifiez la configuration réelle sur le serveur.
- Évaluez les conséquences sur les noms du tailnet, la confidentialité des requêtes et l'accès distant.
- Si un recours public est retenu, définissez ses conditions d'utilisation et le retour au réglage initial.
- Faites approuver le choix avant de modifier le DNS.
- Documentez la procédure retenue et ses résultats attendus dans [maintenance.md](maintenance.md).
- Vérifiez que la procédure conserve l'accès distant et prévoit un retour au réglage initial.

#### Critères de réussite

- Le choix du DNS est approuvé avant modification.
- La procédure conserve l'accès distant au serveur.
- La procédure prévoit un retour au réglage initial.
- La procédure est documentée dans [maintenance.md](maintenance.md).

### Les modes d'accès d'un microservice

#### Objectif

Énumérer les modes d'accès possibles d'un microservice. Les tâches AdGuard Home et WoL demandent ce choix avant toute installation.

#### Conditions

Le mode d'accès décide du pare-feu et de la sortie du compagnon. Aucun mode n'est défini aujourd'hui.

#### Étapes

- Recensez les besoins : le tailnet seul, le réseau local, un accès public.
- Décrivez pour chaque mode son adresse d'écoute et son accès.
- Ajoutez le terme « mode d'accès » au glossaire de [guidelines.md](guidelines.md).
- Remplacez « Définissez le mode d'accès » dans les tâches concernées.

#### Critères de réussite

- Chaque mode porte une adresse d'écoute et une règle d'accès.
- Les tâches AdGuard Home et WoL citent un mode choisi.
- Le glossaire définit le terme « mode d'accès ».

### La procédure générique de déploiement d'un microservice

#### Objectif

Écrire une procédure réutilisable pour créer, transférer et construire un microservice. [maintenance.md](maintenance.md) ne décrit que la voie 2.

#### Conditions

Les sources du service existent dans le dépôt. L'utilisateur donne son accord avant toute écriture sur le serveur.

#### Étapes

- Ajoutez une section qui crée le répertoire du projet dans `/opt`.
- Ajoutez le transfert des sources depuis le Mac.
- Ajoutez la construction de l'image et la création du conteneur.
- Indiquez où exécuter `adguard/verif.sh` et son résultat attendu.

#### Critères de réussite

- La procédure s'applique à un projet autre que la voie 2.
- Chaque étape nomme sa commande et son résultat attendu.
- `adguard/verif.sh` a un résultat attendu documenté.

### Le trajet DNS de chaque voie

#### Objectif

Documenter où un appareil résout un nom, pour la voie 1 et pour la voie 2. Aucun des sept fichiers ne donne ce trajet.

#### Conditions

L'arbitrage DNS reste ouvert dans la tâche « Le réglage DNS d'AdGuard Home ».

#### Étapes

- Relevez le résolveur utilisé par un appareil du tailnet sur chaque voie.
- Relevez le résolveur du conteneur qui relaie le trafic.
- Ajoutez le trajet dans [architecture.md](architecture.md).
- Ajoutez les commandes de contrôle dans [maintenance.md](maintenance.md).

#### Critères de réussite

- Le trajet DNS est décrit pour les deux voies.
- Une commande permet de vérifier le résolveur actif.
- Le réglage de `--accept-dns` est expliqué.

### La démonstration du fail-closed

#### Objectif

Mesurer le comportement d'un client quand le tunnel Nym tombe. [architecture.md](architecture.md) annonce un comportement fail-closed sans mesure.

#### Conditions

Un créneau permet de couper le tunnel. Le client de test est disponible sur le Mac.

#### Étapes

- Arrêtez le tunnel Nym sur le serveur.
- Demandez une page web au client avec `<OLD-NODE-EXIT-NYMVPN>` sélectionné.
- Notez le résultat, l'erreur ou le délai obtenu.
- Rétablissez le tunnel et vérifiez le relais.

#### Critères de réussite

- Le client n'atteint aucun site par l'adresse de la `<ISP-BOX>`.
- Le résultat est consigné avec sa date dans [logbook.md](logbook.md).
- [architecture.md](architecture.md) décrit le comportement observé.

## Les évolutions du projet

Ces évolutions concernent les services et leur documentation. Leur conception précède les changements de configuration. Le cheminement documentaire est défini dans [guidelines.md](guidelines.md), section « Le cheminement d'une modification ».

### Le conteneur Nym pour le mixnet

#### Objectif

Ajouter un conteneur Nym pour le mixnet. Son rôle et son intégration sont définis avant le déploiement.

#### Conditions

Le conteneur Nym pour le mixnet n'existe pas encore. Sa conception précède son déploiement.

#### Étapes

- Définissez le rôle du conteneur Nym.
- Définissez son intégration avec les services existants.
- Déployez le conteneur après validation de la conception.

#### Critères de réussite

- Le rôle du conteneur est documenté.
- Son intégration est validée avec les services existants.
- Le conteneur Nym est déployé.

### Le renommage des services

#### Objectif

Renommer les services avec des noms qui expriment leur rôle. Les références sont mises à jour dans les configurations, les scripts et la documentation.

#### Conditions

Le renommage touche les configurations, les scripts et la documentation. Chaque composant dépendant est identifié avant le changement.

#### Étapes

- Choisissez des noms qui expriment le rôle des services.
- Identifiez les composants qui dépendent de chaque service.
- Mettez à jour les références dans les configurations, les scripts et la documentation.
- Vérifiez le fonctionnement d'ensemble après le renommage.

#### Critères de réussite

- Chaque service porte un nom qui exprime son rôle.
- Aucune référence ancienne ne subsiste.
- Le fonctionnement d'ensemble est vérifié.

### Le nettoyage de l'environnement de diagnostic

#### Objectif

Retirer les éléments de diagnostic devenus inutiles sur le Mac. Colima et Docker ont servi à créer le client Tailscale `ts-client` sur le Mac. Ce client a créé le nœud `ts-test-1` dans le tailnet. Les scripts de diagnostic restent utilisés par les procédures de [maintenance.md](maintenance.md).

#### Conditions

Colima, Docker ou Lima servent peut-être encore à d'autres projets. Le périmètre du nettoyage est approuvé avant toute suppression. La documentation de l'essai décrivait une image `tailscale/tailscale:stable` basée sur Alpine.

#### Étapes

- Vérifiez si Colima, Docker ou Lima servent encore à d'autres projets ou au diagnostic du serveur.
- Faites approuver le périmètre du nettoyage avant toute suppression.
- Si le client doit être retiré, vérifiez le contexte Docker utilisé sur le Mac.
- Dans ce contexte, supprimez uniquement le conteneur de test :

```sh
docker rm -f ts-client
```

- Si l'environnement entier est devenu inutile, retirez la machine virtuelle avant de désinstaller ses outils :

```sh
colima stop
colima delete
brew uninstall colima docker lima
```

- Dans la console Tailscale, vérifiez que `ts-test-1` appartient à cet essai.
- Si ce nœud est devenu inutile, supprimez-le depuis la console.
- Si le client est conservé, vérifiez son image et la disponibilité de `curl` et de `dig`.
- Épinglez l'image utilisée selon [guidelines.md](guidelines.md) avant de reconstruire cet environnement.
- Vérifiez que le nettoyage a retiré les éléments approuvés et conservé les autres usages.

#### Critères de réussite

- Les éléments approuvés sont supprimés.
- Les autres usages de Colima et Docker sont conservés.
- `ts-test-1` est retiré du tailnet s'il est inutile.
- L'image utilisée est épinglée selon [guidelines.md](guidelines.md).

### Les règles nft temporaires

#### Objectif

Vérifier l'absence de résidu de règles nft sur le serveur. La documentation du diagnostic mentionnait deux règles marquées `TEMPO`. Elle indiquait leur disparition avec les recréations du conteneur `nym`.

#### Conditions

La sortie ne doit contenir aucune règle marquée `TEMPO`. Le contrôle se fait sur le serveur.

#### Étapes

- Sur le serveur, relevez la chaîne concernée :

```sh
doas docker exec nym nft list chain inet nym forward
```

- Vérifiez l'absence de règle marquée `TEMPO` dans la sortie.
- Si une règle subsiste, identifiez son rôle avant de proposer son retrait.
- Faites approuver la correction avant de modifier le pare-feu.

#### Critères de réussite

- La sortie ne contient aucune règle marquée `TEMPO`.
- Chaque règle subsistante a un rôle identifié.
- Le pare-feu n'est modifié qu'après approbation.

### Les sources de la voie 1 dans le dépôt

#### Objectif

Verser les sources de `/opt/tailscale` dans le dépôt. [guidelines.md](guidelines.md) les exige pour tout projet Compose. Seul le digest est consigné aujourd'hui.

#### Conditions

Le fichier `.env` ne rejoint jamais le dépôt. Seules les valeurs de configuration sans secret sont versées.

#### Étapes

- Copiez le compose et le `.env.example` dans un répertoire du dépôt.
- Consignez le digest complet de l'image.
- Ajoutez un `.gitignore` qui exclut le `.env`.
- Vérifiez que le dépôt ne contient aucun secret.

#### Critères de réussite

- Le projet de la voie 1 est reconstructible depuis le dépôt.
- Le digest de l'image est complet et épinglé.
- Aucun secret ne figure dans le dépôt.

## Les phases restantes

Quatre phases restent ouvertes. [readme.md](readme.md) donne leur état global. Chaque phase a sa tâche ici.

### Le microservice AdGuard Home

#### Objectif

Ajouter le microservice AdGuard Home. Ses sources existent déjà, avec `adguard/verif.sh`. Elles ne sont pas déployées sur le serveur.

#### Conditions

Le résolveur AdGuard dépend de l'arbitrage DNS en cours. Le mode d'accès du service est défini avant le déploiement.

#### Étapes

- Définissez le mode d'accès du service avant toute installation.
- Appliquez les règles de [guidelines.md](guidelines.md), section « La configuration des microservices ».
- Ajoutez un conteneur compagnon si le service a besoin d'une adresse propre.
- Définissez la sortie sur `<OLD-SERVER-NAME>`, `<OLD-NODE-EXIT-NYMVPN>` ou `none`.
- Changez la sortie avec [maintenance.md](maintenance.md), section « La sortie d'un microservice ».
- Suivez le gabarit de la phase C en annexe.
- Vérifiez le fonctionnement du service après son déploiement.

#### Critères de réussite

- AdGuard Home est déployé.
- Le service possède un mode d'accès défini.
- La sortie du service correspond au choix.
- Les critères dépendent du mode d'accès retenu.

#### Annexe : le gabarit de la phase C

Pour chaque service à ajouter, définissez d'abord le mode d'accès. Un conteneur compagnon fournit une identité Tailscale propre au service. Le schéma présente l'option d'un accès Tailscale indépendant.

```
             Microservice à ajouter
                       │
             tailscaled compagnon
                       │
          ┌────────────┼────────────┐
          │            │            │
        <OLD-SERVER-NAME>       <OLD-NODE-EXIT-NYMVPN>        none
          │            │            │
    Sortie directe  Sortie Nym  Sans exit node
```

Pour ajouter un service, appliquez les règles de [guidelines.md](guidelines.md), section « La configuration des microservices ». Si le service nécessite une adresse Tailscale propre, ajoutez un conteneur compagnon. Si un choix de sortie indépendant est nécessaire, configurez ce compagnon pour ce choix.

Définissez alors la sortie sur `<OLD-SERVER-NAME>`, `<OLD-NODE-EXIT-NYMVPN>` ou `none`. Pour vérifier la sortie et la changer en service, utilisez [maintenance.md](maintenance.md), section « La sortie d'un microservice ». Les critères de réussite dépendent du mode d'accès retenu.

Le choix du résolveur AdGuard attend l'arbitrage de la section « Les étapes communes ». Le drapeau `--accept-routes=true` permet au compagnon de suivre la route de l'exit node. Le changement de sortie utilise `tailscale set` et conserve le conteneur.

### Le microservice WoL

#### Objectif

Ajouter le microservice WoL pour le réveil d'un ordinateur à distance. Le serveur Linux sert aussi de nœud de réveil, comme le consigne le tableau archivé de [logbook.md](logbook.md).

#### Conditions

L'ordinateur à réveiller reste allumé sur le réseau local ou admet le réveil à distance. Le mode d'accès du service est défini avant le déploiement.

#### Étapes

- Définissez le mode d'accès du service avant toute installation.
- Appliquez les règles de [guidelines.md](guidelines.md), section « La configuration des microservices ».
- Ajoutez un conteneur compagnon si le service a besoin d'une adresse propre.
- Définissez la sortie sur `<OLD-SERVER-NAME>`, `<OLD-NODE-EXIT-NYMVPN>` ou `none`.
- Suivez le gabarit de la phase C en annexe.
- Réservez l'adresse IP du serveur sur le réseau local. La réservation ne sert qu'au jour du WoL.
- Vérifiez le réveil d'un ordinateur après le déploiement.

#### Critères de réussite

- WoL est déployé.
- Le réveil d'un ordinateur à distance fonctionne.
- Le service possède un mode d'accès défini.
- L'adresse IP du serveur est réservée sur le réseau local.

### La surveillance et les notifications avec ntfy

#### Objectif

Ajouter la surveillance et les notifications avec ntfy. Une alerte couvre la coupure de l'anonymiseur. Une autre alerte couvre la coupure de courant.

#### Conditions

Le serveur peut être indisponible pendant une coupure de courant. L'émission de l'alerte est définie pour ce cas.

#### Étapes

- Prévoyez une alerte pour une coupure de l'anonymiseur.
- Prévoyez une alerte pour une coupure de courant.
- Pour une coupure de courant, définissez comment l'alerte peut être émise lorsque le serveur est indisponible.
- Vérifiez qu'une alerte correspond à chaque situation.

#### Critères de réussite

- Une alerte signale la coupure de l'anonymiseur.
- Une alerte signale la coupure de courant.
- Chaque situation déclenche une alerte.
- L'émission reste possible quand le serveur est indisponible.

### Le repo GitHub privé

#### Objectif

Créer un dépôt GitHub privé pour les sources et la documentation. [readme.md](readme.md) en est la page d'accueil.

#### Conditions

Les sept fichiers sont validés. Le dépôt contiendra `tailscale-nym/`, `adguard/` et cette documentation.

#### Étapes

- Créez le dépôt GitHub privé.
- Ajoutez `tailscale-nym/`, `adguard/` et cette documentation.
- Vérifiez que les secrets restent hors du dépôt.
- Vérifiez que les fichiers correspondent au périmètre validé.
- Publiez [readme.md](readme.md) comme page d'accueil.

#### Critères de réussite

- Le dépôt est privé.
- Le dépôt contient `tailscale-nym/`, `adguard/` et la documentation.
- Aucun secret n'est présent dans le dépôt.
- [readme.md](readme.md) est la page d'accueil.

## Les défauts connus, non corrigés

Cette section liste les défauts connus qui restent ouverts. Chaque défaut devient une tâche avec ses étapes et ses critères. Les constats sont conservés tels quels.

### Le domaine réglementaire Wi-Fi

#### Objectif

`iw reg get` renvoie `country 00: DFS-UNSET`. Tous les canaux sont en `PASSIVE-SCAN`. Le domaine réglementaire n'a jamais été posé. C'est un défaut connu avec `iwlwifi`. L'objectif est de poser le domaine réglementaire.

#### Conditions

La commande exige une désassociation Wi-Fi. La correction demande une présence sur place.

#### Étapes

- Avec quelqu'un sur place, exécutez `iw reg set FR`.
- Vérifiez `iw reg get` après l'exécution.

#### Critères de réussite

- `iw reg get` affiche le domaine `FR`.
- Les canaux ne restent pas tous en `PASSIVE-SCAN`.
- La liaison Wi-Fi fonctionne après la commande.

### La limite de wpa_supplicant

#### Objectif

`wpa_supplicant` tourne sous `supervise-daemon` avec `--respawn-max 5 --respawn-period 1800`. Au-delà de cinq redémarrages en 30 minutes, le superviseur renonce. Le serveur reste alors sans liaison Wi-Fi. L'objectif est d'éviter cette perte de liaison.

#### Conditions

Cinq redémarrages en 30 minutes arrêtent la supervision. Le défaut laisse le serveur sans liaison Wi-Fi.

#### Étapes

- Identifiez la cause des redémarrages de `wpa_supplicant`.
- Corrigez la cause pour rester sous la limite.
- Vérifiez le comportement du superviseur après la correction.
- Vérifiez la liaison Wi-Fi après plusieurs redémarrages.

#### Critères de réussite

- `wpa_supplicant` ne dépasse pas la limite de supervision.
- Le superviseur relance le service sans renoncer.
- Le serveur garde sa liaison Wi-Fi.

### La dépendance DNS du Mac

#### Objectif

Les résolveurs du Mac sont `100.100.100.100` et `fd7a:115c:a1e0::53`, donc MagicDNS. Toute résolution de nom dépend du tailnet, donc du Wi-Fi instable. C'est une seconde cause de « ça marche à peu près ». Le contournement consiste à garder MagicDNS et à ajouter un résolveur public en second. Rien n'a été modifié. L'objectif est d'appliquer ce contournement.

#### Conditions

Le Wi-Fi instable justifie le contournement. Le changement attend une décision de l'utilisateur.

#### Étapes

- Demandez l'accord avant de modifier le DNS du Mac.
- Gardez MagicDNS comme résolveur principal.
- Ajoutez un résolveur public en second.
- Vérifiez la résolution des noms après le changement.

#### Critères de réussite

- MagicDNS reste le résolveur principal.
- Un résolveur public répond en second.
- La résolution des noms fonctionne hors du tailnet.

### Le redémarrage non revérifié depuis 2026-10-05

#### Objectif

Le redémarrage complet n'a pas été revérifié depuis la reconfiguration réseau du 2026-10-05. Le test du 2026-10-03 avait réussi sur l'état d'avant. La configuration est persistante et validée par `ifup -n`. Le gardien est au runlevel `default`. Le service `networking` continue la boucle si `eth0` échoue. Le risque est faible, mais l'essai reste à faire. L'objectif est de revérifier le redémarrage complet.

#### Conditions

Ce test suit toute reconfiguration réseau. Ici, la reconfiguration du 2026-10-05 n'a pas été revérifiée.

#### Étapes

- Redémarrez le serveur avec `doas reboot`.
- Reconnectez-vous au serveur après le redémarrage.
- Appliquez les contrôles de [maintenance.md](maintenance.md), section « Le redémarrage de l'hôte ».
- Vérifiez le relais selon [maintenance.md](maintenance.md), section « La vérification des sorties ».

#### Critères de réussite

- Les conteneurs `tailscale`, `<OLD-NETNS>`, `nym` et `<OLD-NODE-EXIT-NYMVPN>` sont `Up`.
- `<OLD-SERVER-NAME>` garde `<TAILNET-IP-EXIT-DIRECT>`.
- `<OLD-NODE-EXIT-NYMVPN>` garde `<TAILNET-IP-EXIT-NYMVPN>`.
- La route vers la passerelle utilise `eth0`.
- Les deux sorties fonctionnent après le redémarrage.

## Le conditionnel

Cette section liste les travaux qui attendent une condition. La condition est nommée pour chaque travail. Aucun de ces travaux ne bloque une autre étape.

### L'exposition publique des services

#### Objectif

Exposer les services publiquement seulement quand le besoin réel arrive. L'exposition demande un reverse-proxy et un domaine.

#### Conditions

Les services restent accessibles par le tailnet seulement. Le besoin réel d'exposition publique n'est pas encore arrivé.

#### Étapes

- Obtenez la décision explicite de l'utilisateur.
- Installez un reverse-proxy.
- Déclarez un domaine pour les services.
- Vérifiez l'accès public de chaque service.

#### Critères de réussite

- Chaque service exposé a un besoin documenté.
- L'exposition utilise un reverse-proxy et un domaine.
- L'accès par le tailnet reste possible.

### La redondance du disque

#### Objectif

Ajouter la redondance du disque quand le serveur héberge une donnée précieuse. La sauvegarde attend la même condition.

#### Conditions

La redondance sera décidée quand le disque contiendra des données précieuses. Aucune donnée précieuse n'est hébergée aujourd'hui.

#### Étapes

- Ajoutez la redondance du disque.
- Ajoutez la sauvegarde des données.
- Vérifiez la restauration depuis la sauvegarde.

#### Critères de réussite

- Le disque dispose d'une redondance.
- Les données sont sauvegardées.
- Une restauration est réussie.

### La nappe de la batterie

#### Objectif

Débrancher la nappe de la batterie. La batterie est gonflée et le châssis est déformé.

#### Conditions

La batterie est gonflée et le châssis est déformé. L'opération est planifiée sans urgence.

#### Étapes

- Planifiez l'opération sans urgence.
- Débranchez la nappe de la batterie.
- Vérifiez le démarrage du serveur après le débranchement.

#### Critères de réussite

- La nappe est débranchée.
- Le serveur démarre sans la batterie.

### Le nettoyage des images Docker

#### Objectif

Nettoyer les images Docker inutilisées. Cette opération reste facultative.

#### Conditions

Cette opération reste facultative. Aucune image utilisée ne doit être supprimée.

#### Étapes

- Listez les images Docker inutilisées.
- Retirez uniquement les images sans conteneur.
- Vérifiez le redémarrage des services après le nettoyage.

#### Critères de réussite

- Les images inutilisées sont retirées.
- Les images des services restent disponibles.
- Les services redémarrent sans erreur d'image.

### La réinscription du nœud `<OLD-SERVER-NAME>`

#### Objectif

Rétablir l'identité du nœud `<OLD-SERVER-NAME>` quand aucune clé d'authentification ne reste. [logbook.md](logbook.md) consigne ce cas le 2026-10-01.

#### Conditions

L'utilisateur fournit une clé d'authentification. Son accord précède toute écriture sur la voie 1.

#### Étapes

- Obtenez la clé d'authentification de l'utilisateur.
- Recréez le conteneur avec [maintenance.md](maintenance.md), section « La mise à jour de la voie directe ».
- Vérifiez que le nœud reprend `<TAILNET-IP-EXIT-DIRECT>`.
- Consignez la reprise sans recopier la clé.

#### Critères de réussite

- Le nœud `<OLD-SERVER-NAME>` est de nouveau approuvé comme exit node.
- La clé ne figure dans aucun fichier suivi par Git.
- Le résultat est consigné dans [logbook.md](logbook.md).
