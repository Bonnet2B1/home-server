# Serveur domestique sur laptop `<SERVER-MODEL>`

Ce fichier présente le projet et la carte de la documentation.

## Le projet

Le serveur est un laptop `<SERVER-MODEL>`. Il tourne sous Alpine avec Docker. Il fait partie d'un tailnet Tailscale.

Le tailnet offre deux sorties Internet. Chaque appareil choisit sa sortie dans l'app Tailscale.

- Voie 1 : le nœud `<OLD-SERVER-NAME>`, avec une sortie directe par la `<ISP-BOX>`.
- Voie 2 : le nœud `<OLD-NODE-EXIT-NYMVPN>`, avec une sortie anonymisée par Nym en mode fast.

Les deux voies sont en service depuis le 2026-10-03.

Lisez `reasons.md` pour savoir pourquoi le serveur existe et pourquoi chaque technologie a été choisie.

## Les sept fichiers

Chaque fichier a un axe. Pour trouver une information, ouvrez le fichier de l'axe correspondant. Le tableau ci-dessous donne les sept fichiers.

| Fichier | Axe | Contenu |
|---|---|---|
| `readme.md` | Présentation | Le projet, l'avancement, la carte de la documentation |
| `guidelines.md` | Règles | Les conventions et les interdits |
| `reasons.md` | Pourquoi | Les décisions, la menace, les choix technologiques |
| `architecture.md` | Présent | L'état réel, les schémas, les explications |
| `operations.md` | Procédures | Les commandes d'exploitation |
| `runbook.md` | Passé | Les incidents, les diagnostics, les pièges |
| `todo.md` | Futur | Les tâches restantes et les cas conditionnels |

La section « L'état réel de la machine » de `architecture.md` est la source de vérité. Elle prime sur les six autres fichiers. Tout le reste est une intention, une décision ou une archive.

## État global

Mettez à jour ce tableau après chaque étape. Les trois dernières cases sont à faire. Chacune a une fiche dans `todo.md`.

- [x] Alpine 3.24 est installé sur le laptop `<SERVER-BRAND>`. Le nom d'hôte est `<OLD-SERVER-NAME>`.
- [x] SSH accepte la clé seule. `PasswordAuthentication` vaut `no`. La connexion root est désactivée.
- [x] L'utilisateur `<ADMIN-ACCOUNT>` et `doas` sont configurés.
- [x] Docker 29.5.x et compose v5.1.4 sont installés. Docker démarre au boot.
- [x] L'Ethernet `eth0` est en service depuis le 2026-10-05, avec repli automatique sur le Wi-Fi.
- [x] La voie 1, nommée `<OLD-SERVER-NAME>`, est construite et testée. Son identité est persistante depuis le 2026-10-03.
- [x] La voie 2, nommée `<OLD-NODE-EXIT-NYMVPN>`, a un tunnel Nym établi. Son relais est vérifié depuis le 2026-10-03.
- [ ] Phase C : les microservices AdGuard Home et WoL.
- [ ] Phase D : la surveillance et les notifications ntfy.
- [ ] Le repo GitHub privé. `readme.md` en sera la page d'accueil.
