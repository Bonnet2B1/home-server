# Guidelines : les règles du projet

Ce fichier énonce les règles. Il ne donne pas leur raison. La raison est dans `reasons.md`. L'événement qui a produit la règle est dans `runbook.md`.

Lisez ce fichier avant d'agir.

## Les conventions

- Format des dates : `AAAA-MM-JJ`.
- Chaque service vit dans `/opt/<service>`. Le répertoire appartient à root.
- Chaque projet compose possède son propre fichier `.env`.
- Le fichier `.env` est en mode `600`. Il reste hors du repo. Le fichier `.env.example` est le gabarit. Le `.gitignore` reste strict.
- Chaque image Docker est épinglée par digest. N'utilisez jamais `latest` sans vérification.
- Chaque conteneur qui doit survivre à un redémarrage porte `restart: unless-stopped`.
- Les services restent accessibles par le tailnet seulement.
- N'écrivez pas de script unique avant d'avoir assez de projets. Un script demande sa propre maintenance.
- Mettez la documentation à jour après chaque étape.
- Une tâche vit à un seul endroit. Les autres fichiers font un lien vers elle.

## Les secrets

- Ne cherchez jamais une clé, une graine ou un mot de passe dans les fichiers de l'utilisateur. N'utilisez un secret que si l'utilisateur vous le donne.
- Ne lancez jamais `nym-vpnd -v`. La mnemonic Nym sort dans les journaux au niveau `info`.
- Ne copiez jamais la mnemonic sur le disque de l'hôte. Elle vit dans le volume `nym-data`, au chemin `/var/lib/nym-vpnd/mainnet/mnemonic.json` dans le conteneur.
- Vous voyez `TS_AUTHKEY` en clair dans `docker inspect <OLD-NODE-EXIT-NYMVPN>`. Ce n'est pas une fuite. La variable passe par l'environnement du conteneur.

## Docker

- Ne lancez jamais `docker rm -f` avec un motif de nom. Ciblez le nom exact du conteneur. Ou laissez `docker compose down` agir projet par projet.
- Les deux voies vivent sur le même hôte. Un motif de nom commun frappe les deux voies. L'incident du 2026-10-01 est dans `runbook.md`, section « L'incident du 2026-10-01 ».
- Après un rebuild de `nym`, ne lancez pas `docker compose up -d` sans argument. Utilisez `docker compose up -d --no-deps nym`. La raison de cette règle est dans `operations.md`.
- Ne recréez jamais `<OLD-NETNS>` seul. Recréez aussi `nym` et `<OLD-NODE-EXIT-NYMVPN>`, car l'espace réseau appartient à `<OLD-NETNS>`.

## Le réseau

- Ne coupez jamais `wlan0`. Il sert de repli. `uplink-guard` ne le touche jamais.
- Ne posez jamais le domaine réglementaire avec `iw reg set FR` à distance. Ne modifiez jamais `wpa_supplicant` à distance. Les deux opérations exigent une désassociation Wi-Fi. La désassociation coupe l'accès à une machine sans accès physique. Faites-les uniquement avec quelqu'un sur place.
- L'instabilité se corrige avec l'épinglage de la passerelle. Elle ne se corrige pas avec les sysctl ARP. Laissez `arp_ignore` et `arp_announce` à leurs valeurs par défaut.
- Ne répétez jamais `ip route replace` sur la route épinglée. La commande supprime puis recrée la route. Elle crée une micro-coupure. Le gardien ne touche à la route que si l'état diffère.

## La voie 1 et la voie 2

- N'écrivez rien sur la voie 1 sans l'accord de l'utilisateur.
- Vous pouvez écrire librement sur la voie 2.
- N'utilisez pas `network_mode: host` pour la voie 2. Une route par défaut mal placée casserait la route de l'hôte. La voie 1 deviendrait injoignable.
- N'exposez jamais un service sur Internet par vous-même. L'exposition publique est une décision séparée et différée.

## La modalité de travail

- L'agent propose les commandes et les exécute. L'utilisateur colle les sorties de chaque commande. L'agent les lit lui-même s'il a l'accès.
- L'utilisateur saisit son mot de passe `doas`.
- L'utilisateur garde la main sur la voie 1.

## Le style de la documentation

- Utilisez l'impératif pour les procédures. Utilisez l'indicatif présent pour l'état.
- Une case cochée décrit un travail fait. Elle ne prouve pas que l'objet existe encore.
- Un piège est un titre `#####`. Il n'est pas un paragraphe en gras. Il doit entrer dans la table des matières et pouvoir être lié.
- La section « L'état réel de la machine » de `architecture.md` prime sur les autres fichiers.
