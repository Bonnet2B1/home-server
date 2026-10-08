# Transformer un vieux laptop en serveur domestique

Le projet réutilise un vieux laptop comme serveur domestique. Il vise la décentralisation et la souveraineté : héberger ses services et garder le contrôle de ses données. Il utilise Tailscale pour l'accès privé et Nym pour la sortie Internet dédiée à l'anonymat. Le tailnet offre deux nœuds de sortie. Chaque appareil choisit sa voie dans l'application Tailscale.

## La documentation

Les rôles des fichiers sont définis dans [guidelines.md](guidelines.md), section « Le rôle des fichiers ». [architecture.md](architecture.md) décrit l'état actuel du système. [logbook.md](logbook.md) conserve les événements passés.

- [readme.md](readme.md) — `Présentation du projet`
- [philosophy.md](philosophy.md) — `Objectifs, menace et principes`
- [guidelines.md](guidelines.md) — `Règles et vocabulaire`
- [architecture.md](architecture.md) — `Services et fonctionnement`
- [maintenance.md](maintenance.md) — `Entretien et diagnostic`
- [logbook.md](logbook.md) — `Historique des décisions et des essais`
- [todo.md](todo.md) — `Travaux restants et critères de réussite`

## État global

Cet aperçu regroupe les fonctions du serveur. Les étapes et les critères détaillés sont dans [todo.md](todo.md).

- [x] Alpine : système minimal pour réutiliser le vieux laptop.
- [x] SSH : accès distant chiffré, avec authentification par clé.
- [x] Docker : hébergement des services dans des conteneurs.
- [x] Ethernet : liaison principale, avec le Wi-Fi en repli.
- [x] Tailscale : accès privé au serveur et sortie Internet directe.
- [x] Mode fast : sortie Internet par l'anonymiseur Nym.
- [ ] [AdGuard Home](todo.md#le-microservice-adguard-home) : filtrage des requêtes DNS.
- [ ] [WoL](todo.md#le-microservice-wol) : réveil d'un ordinateur à distance.
- [ ] [ntfy](todo.md#la-surveillance-et-les-notifications-avec-ntfy) : alertes de coupure de l'anonymiseur ou de courant.
- [ ] [Nym mixnet](todo.md#le-conteneur-nym-pour-le-mixnet) : conteneur dédié au mixnet.
- [ ] [GitHub](todo.md#le-repo-github-privé) : dépôt privé pour les sources et la documentation.
