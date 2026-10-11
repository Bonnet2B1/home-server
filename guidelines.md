# Guidelines : les règles du projet

Ce fichier fixe les règles de travail, de codage, de configuration et de documentation. Il contient aussi le vocabulaire commun. Appliquez les règles présentes dans ce fichier.

Ce fichier évolue avec le projet, comme le reste de la documentation. Avant de modifier une règle, obtenez l'accord de l'utilisateur. Appliquez ensuite la version approuvée.

## Le travail

- Avant une correction, consultez les sources pertinentes pour comprendre le comportement actuel.
- Présentez le changement prévu et ses conséquences avant de l'appliquer.
- Obtenez l'accord de l'utilisateur avant toute correction.
- Si une décision reste incertaine, demandez à l'utilisateur de la trancher.
- Avant de modifier la voie 1, obtenez l'accord de l'utilisateur.
- L'agent peut modifier la voie 2 sans autorisation supplémentaire pour chaque commande d'une intervention approuvée.
- L'agent exécute les commandes lorsqu'il dispose de l'accès nécessaire.
- Si l'agent ne dispose pas de cet accès, l'utilisateur exécute les commandes et transmet les sorties.
- L'utilisateur saisit son mot de passe `doas`.
- Conservez les faits historiques lors d'une réorganisation de la documentation.
- Avant de corriger un fait historique, présentez la correction à l'utilisateur.

## Le codage et la configuration

- Choisissez des noms qui expriment le rôle des services.
- Avant d'ajouter un outil ou une automatisation, identifiez le besoin qu'il couvre.
- Privilégiez une solution existante lorsqu'elle répond à ce besoin.
- Limitez chaque modification au besoin identifié.
- Pour supprimer ou recréer une ressource, ciblez son nom exact.
- Limitez chaque opération aux services concernés.
- Avant de modifier un composant, identifiez les composants qui dépendent de lui.
- Vérifiez le fonctionnement d'ensemble, en plus de chaque composant.
- Préservez les données et les identités persistantes lors d'une modification.
- Vérifiez le résultat avec les critères définis dans [todo.md](todo.md).

### La configuration des microservices

- Placez chaque projet Compose dans `/opt/<service>`.
- Donnez le répertoire du projet à root.
- Épinglez les images distantes par digest et les images locales par version.
- Pour un conteneur qui doit reprendre après un redémarrage, définissez `restart: unless-stopped`.
- Vérifiez la compatibilité des configurations des composants qui échangent des données.
- Avant le déploiement, réglez les incompatibilités identifiées.

### Les secrets

- Ne cherchez jamais une clé, une graine ou un mot de passe dans les fichiers de l'utilisateur.
- N'utilisez un secret que si l'utilisateur vous le donne.
- Conservez les secrets dans le stockage prévu pour le service.
- Pour les variables secrètes du projet Compose, utilisez un fichier `.env` en mode `600`.
- Excluez les secrets du dépôt avec `.gitignore`.
- Versionnez un fichier `.env.example` contenant les noms des variables et des valeurs non secrètes.
- Ne lancez pas de commande qui affiche des secrets.
- Traitez les sorties contenant des secrets comme des données sensibles.
- Avant de partager une sortie ou de la consigner, masquez les secrets.

### Le masquage avant publication

Le dépôt est publié sur GitHub. Avant publication, masquez toute valeur qui identifie l'utilisateur ou son réseau. Un filtre Git applique le masquage au commit. Un hook `pre-commit` vérifie l'index.

- Écrivez les valeurs réelles dans le dépôt local. Le filtre les remplace par des jetons au commit.
- Utilisez un jeton stable pour une même entité, sur toutes ses occurrences.
- En prose, entourez le jeton de backticks. GitHub interprète `<TOKEN>` comme du HTML brut et l'efface à l'affichage.
- Dans un diagramme Mermaid, écrivez le jeton entre guillemets. Mermaid prend `<TOKEN>` pour une balise et le supprime.
- Conservez les correspondances dans `sanitize.map`. Ce fichier est ignoré par Git.
- Après un clone neuf, exécutez `tools/install-filters.sh` pour activer le filtre et le hook.
- Les règles de poussée figurent dans la section « Les règles Git et de push ».
- Le nom du tailnet reste en clair. Il figure dans l'URL du dépôt, donc le masquer n'ajouterait rien. Le domaine du tailnet reste masqué.

Le tableau donne la légende des jetons.

| Jeton | Valeur masquée |
|---|---|
| `<WAN-IP-BOX-A>`, `<WAN-IP-BOX-B>` | Adresses publiques de la box, relevées à deux dates. |
| `<ISP>`, `<ISP-BOX>` | Fournisseur d'accès Internet et sa box. |
| `<TAILNET-DOMAIN>` | Domaine du tailnet. |
| `<TAILNET-IP-EXIT-DIRECT>` | Adresse Tailscale du nœud de sortie directe. |
| `<TAILNET-IP-EXIT-NYMVPN>` | Adresse Tailscale du nœud de sortie Nym. |
| `<TAILNET-IP-CLIENT>` | Adresse Tailscale du client MacBook. |
| `<TAILNET-IP-TS-TEST>` | Adresse Tailscale du client de test. |
| `<TAILNET-IP-OLD-IDENTITY>` | Ancienne adresse Tailscale d'un nœud retiré. |
| `<LAN-SUBNET>` | Sous-réseau du réseau local. |
| `<LAN-IP-SERVER>` | Adresse locale du serveur. |
| `<LAN-IP-WIFI>` | Adresse locale de l'interface Wi-Fi. |
| `<LAN-GATEWAY-IP>` | Adresse locale de la box. |
| `<COLIMA-GATEWAY-IP>` | Adresse de la passerelle de l'environnement Colima. |
| `<DOCKER-INTERNAL-IP>` | Adresse interne d'un réseau Docker. |
| `<MAC-ETH0>` | Adresse matérielle de l'interface Ethernet. |
| `<HOST-MACBOOK>` | Nom du client MacBook. |
| `<HOST-IPHONE>` | Nom du client iPhone. |
| `<SERVER-MODEL>` | Modèle du laptop serveur. |
| `<SERVER-BRAND>` | Marque du laptop serveur. |
| `<OLD-SERVER-NAME>` | Ancien nom d'hôte du serveur. |
| `<OLD-NODE-EXIT-NYMVPN>` | Ancien nom du conteneur de sortie Nym. |
| `<OLD-NETNS>` | Ancien nom de l'espace réseau. |
| `<ADMIN-ACCOUNT>` | Nom du compte d'administration SSH. |
| `/Users/<LOCAL-USER>` | Répertoire du dépôt sur le poste local. |

### Les règles Git et de push

Ces règles couvrent la poussée du dépôt public et la protection des valeurs qui changent.

- Poussez seulement avec l'accord explicite de l'utilisateur.
- Poussez uniquement la branche `main`.
- N'utilisez jamais `git push --mirror`. Cette commande publierait les refs internes.
- Ne réécrivez pas l'historique déjà publié sans l'accord de l'utilisateur.
- Purgez les refs `t3/*` avant chaque push. Expirez ensuite le reflog et vérifiez `git fsck`.
- Vérifiez l'index avec `tools/check_leaks.py` avant de pousser. Le hook `pre-commit` fait ce contrôle à chaque commit.
- Le hook `commit-msg` applique les mêmes contrôles aux messages de commit.
- Quand l'adresse publique change, mettez à jour `sanitize.map` avec `tools/wan_ip.py update`.
- Le hook `pre-commit` exécute `tools/wan_ip.py check`. Il bloque un commit qui contient l'adresse publique actuelle en clair.

### Le réseau

- Séparez l'espace réseau de la voie anonymisée de celui de l'hôte.
- Conservez une liaison de repli disponible.
- Pour modifier les paramètres de la liaison de repli, exigez une présence sur place.
- Avant de changer un paramètre réseau, vérifiez le besoin et l'espace réseau concernés.
- Limitez le changement à cet espace réseau.
- Si l'état souhaité est déjà obtenu, conservez-le sans réappliquer le changement.
- Gardez les services accessibles par le tailnet.
- Avant une exposition publique, obtenez une décision explicite de l'utilisateur.

## La documentation

Organisez chaque fichier selon son rôle. Donnez à chaque information une source de référence. Utilisez des liens pour les détails déjà documentés.

### Le rôle des fichiers

Choisissez le fichier selon le rôle de l'information. Respectez l'organisation propre à ce fichier. Le tableau précise le contenu de chacun.

| Fichier | Axe | Contenu |
|---|---|---|
| [readme.md](readme.md) | Présentation | Le projet, les parcours de lecture et l'avancement par fonction. |
| [philosophy.md](philosophy.md) | Principes | Les objectifs, la menace et les principes du projet. |
| [guidelines.md](guidelines.md) | Règles | Les règles de travail, de codage, de configuration et de documentation, ainsi que le vocabulaire commun. |
| [architecture.md](architecture.md) | État actuel | Les composants, leurs relations, les chemins du trafic et les limites connues, décrits par du texte et des schémas. |
| [maintenance.md](maintenance.md) | Maintenance | Les procédures d'entretien, de diagnostic et de réparation du système existant, avec leurs conditions et leurs résultats attendus. |
| [todo.md](todo.md) | Travaux restants | Les tâches à effectuer, avec leur objectif, leurs conditions, leurs étapes et leurs critères de réussite. |
| [logbook.md](logbook.md) | Historique | Les événements datés, les décisions techniques, les essais, les commandes exécutées et les résultats. |

### Le cheminement d'une modification

Avant une nouvelle fonction ou un correctif, inscrivez l'objectif et les critères de réussite dans [todo.md](todo.md). Pendant le travail, consignez les essais, les échecs et les résultats datés dans [logbook.md](logbook.md). Quand les critères de réussite sont vérifiés, mettez à jour l'état réel dans [architecture.md](architecture.md).

Si une modification produit une procédure de maintenance réutilisable, ajoutez-la dans [maintenance.md](maintenance.md). Si elle produit une nouvelle règle, ajoutez-la dans [guidelines.md](guidelines.md). Si elle change un principe du projet, mettez à jour [philosophy.md](philosophy.md).

Une tâche est terminée lorsque ses critères sont vérifiés et que les documents concernés sont à jour. Retirez alors cette tâche de [todo.md](todo.md). Conservez son historique dans [logbook.md](logbook.md).

### La pertinence et le minimalisme

- Documentez ce qui permet de comprendre le système, de prendre une décision ou d'effectuer une opération.
- Remplacez les statuts génériques par une information utile au lecteur.
- Conservez les détails qui expliquent un fonctionnement, une limite ou une conséquence.
- Réduisez les répétitions en renvoyant à la source de référence.
- Choisissez un schéma pour les relations, une liste pour les étapes et un tableau pour les comparaisons.
- Conservez les cas particuliers dans le fichier correspondant à leur rôle.
- Dans [guidelines.md](guidelines.md), formulez la règle générale issue d'un cas particulier.

### La rédaction

- Utilisez l'impératif pour les procédures, le présent pour l'état et le passé pour les événements.
- Limitez les phrases à 20 mots pour les procédures et à 25 mots pour les descriptions.
- Donnez une seule instruction par phrase.
- Présentez la condition avant l'action.
- Pour un avertissement, présentez la consigne avant le risque.
- Utilisez des termes précis.
- Gardez le même sens pour chaque terme.
- Définissez les termes techniques nécessaires dans le glossaire.
- Utilisez « vérifiez » pour les contrôles.
- Choisissez des titres qui indiquent le sujet de la section.
- Pour une information à référencer, choisissez un titre qui permet un lien direct.
- Utilisez des liens relatifs pour les fichiers du dépôt.
- Dans le README, présentez chaque lien documentaire avec son rôle entre backticks.

### La précision et la relecture

- Distinguez les faits vérifiés, les hypothèses et les objectifs.
- Pour un fait actuel, consultez les sources pertinentes avant de l'affirmer.
- Pour un constat passé, conservez la date et le contexte disponibles.
- Si la date manque, indiquez qu'elle n'est pas consignée.
- Traitez une case cochée comme la trace d'un travail terminé.
- Utilisez [architecture.md](architecture.md) comme référence pour l'état actuel du système.
- Pour établir l'état réel, vérifiez directement sur le serveur. La documentation ne remplace pas cette vérification.
- Après une modification, relisez les fichiers concernés et vérifiez leurs renvois.
- Vérifiez les noms, les chemins, les adresses et les valeurs techniques.
- Pour une réorganisation importante, faites relire la documentation par un lecteur sans l'historique du travail.
- Vérifiez qu'il distingue le fonctionnement actuel, les événements passés et les travaux restants.

## Le vocabulaire

Ce glossaire définit les termes nécessaires à la lecture du projet. Les définitions expliquent les concepts. Les configurations propres au serveur sont décrites dans [architecture.md](architecture.md).

| Terme | Définition |
|---|---|
| Agent | Assistant qui aide à la maintenance. Il obtient l'accord de l'utilisateur avant d'écrire. |
| Serveur | Ordinateur qui fournit des services à d'autres appareils. |
| Conteneur | Environnement isolé pour exécuter un service. Certains éléments, dont l'espace réseau, peuvent être partagés. |
| Espace réseau | Ensemble isolé d'interfaces, de routes et de règles de pare-feu. Plusieurs conteneurs peuvent le partager. |
| Exit node | Nœud Tailscale qui relaie le trafic des autres appareils vers Internet. |
| Voie 1 | Sortie Internet directe, par la `<ISP-BOX>`. L'adresse publique est celle de la box. |
| Voie 2 | Sortie Internet par l'anonymiseur Nym, avec deux sauts. |
| Tailnet | Réseau privé d'appareils géré par Tailscale. |
| Table de routage | Ensemble de routes utilisé pour choisir le chemin d'un paquet. |
| Étiquette de paquet, `fwmark` | Valeur attachée à un paquet pour orienter son routage ou son traitement par le pare-feu. |
| Route par défaut | Route utilisée lorsqu'aucune route plus précise ne correspond à la destination. |
| Conteneur compagnon, sidecar | Conteneur qui fournit une fonction complémentaire à un autre conteneur. |
| `--accept-routes=true` | Option d'acceptation des routes annoncées par d'autres nœuds Tailscale. |
| DERP | Relais Tailscale utilisé quand une connexion directe entre pairs n'est pas possible. |
| WireGuard | Protocole de chiffrement utilisé par Tailscale et par le client Nym pour leurs tunnels. |
| MTU | Taille maximale d'un paquet IP transporté sans fragmentation sur une liaison. |
| Anonymiseur | Service qui masque l'adresse d'origine du trafic qu'il relaie. |
| Mode fast | Mode Nym avec deux sauts, une passerelle d'entrée puis une passerelle de sortie. |
| Mixnet | Réseau qui mélange le trafic de plusieurs utilisateurs pour réduire la corrélation entre envoi et réception. |
| `.env` | Fichier de variables utilisé pour la configuration d'un projet Compose. |
| `<ISP-BOX>` | Box d'accès Internet du fournisseur `<ISP>`. |
| WoL | Mécanisme de réveil d'un ordinateur par le réseau local. |
| MagicDNS | Fonction Tailscale qui résout les noms des appareils du tailnet. |
| fail-closed | Comportement qui bloque le trafic protégé quand le tunnel manque, plutôt que de le laisser sortir directement. |
| supervise-daemon | Superviseur OpenRC qui relance un service selon sa configuration. |
| Superviseur | Boucle shell du conteneur Nym. Elle relance le client et répare les règles. |
| Digest | Empreinte du contenu d'une image. Elle identifie l'image à télécharger. |
| sysctl | Interface Linux de lecture et de modification des paramètres du noyau. |
| Graine, mnemonic | Phrase de récupération qui donne accès à une identité ou à un compte. |
