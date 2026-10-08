# Reasons : les raisons du projet

Ce fichier donne les raisons du projet et les décisions actées. La forme opérationnelle de chaque décision est dans `guidelines.md`. Ce qui s'est passé est dans `runbook.md`.

## L'objectif

Un serveur domestique multifonction fait de microservices. Il utilise Alpine avec Docker. Il appartient à un tailnet Tailscale.

Le tailnet doit offrir deux sorties Internet indépendantes. Les deux voies sont en service depuis le 2026-10-03.

## La menace

La menace vient du fournisseur d'accès et des métadonnées. Le mode fast de Nym est retenu parce que le mixnet est trop lent. Le géo-bypass est désactivé. Le client ne signale pas sa localisation au réseau Nym.

## Les choix technologiques

Chaque technologie remplit un besoin précis. La dernière colonne donne l'alternative refusée. `runbook.md` donne le détail des incidents liés à ces choix.

| Technologie | Besoin | Pourquoi celle-ci | Alternative refusée |
|---|---|---|---|
| Alpine 3.24 | Le système d'exploitation | L'utilisateur veut garder Alpine minimal. Il a retiré `ttyd`, `tmux` et le cache des paquets, pour cela et pour des raisons de sécurité. | Une distribution plus lourde |
| Docker et compose | Empiler les microservices | Docker isole les conteneurs. Docker démarre au boot. Les identités vivent dans des volumes qui survivent à une recréation. | Des services natifs Alpine, sans isolation |
| Tailscale | L'accès au serveur et le transport des deux sorties | Le tailnet donne l'accès. Aucun port n'est exposé. Chaque appareil choisit sa sortie dans l'app. | La réservation d'adresse IP locale, réservée au jour du WoL |
| Deux exit nodes | Deux sorties indépendantes | Le choix vaut pour la session. Un appareil ne change pas de voie en cours de session. | Un exit node unique |
| Nym en mode fast | Anonymiser la voie 2 | Le trajet comporte deux sauts, une passerelle d'entrée puis une passerelle de sortie. | Le mixnet, trop lent |
| Espace réseau dédié `<OLD-NETNS>` | Isoler la voie 2 de l'hôte | Une route ou un pare-feu mal placé dans la voie 2 casserait la route de l'hôte. La voie 1 deviendrait injoignable. | `network_mode: host` pour la voie 2 |
| Conteneur `<OLD-NETNS>` dédié | Tenir l'espace réseau | Un espace réseau appartient au conteneur qui le crée. Avec `service:nym`, un redémarrage de `nym` détruirait l'espace. | `network_mode: service:nym` |
| Image `local/tailscale-nft` | Le pare-feu de la voie 2 | L'image officielle pointe `iptables` vers `iptables-legacy`. Le noyau d'Alpine n'expose aucun module `ip_tables`. | L'image officielle Tailscale |
| Backend noyau `TS_USERSPACE=false` | Éviter la confusion des marques | En espace utilisateur, la marque Tailscale `0x80000` et la marque Nym `0x14d` peuvent se confondre. Le trafic repart alors par la table principale. | Le mode espace utilisateur |
| AdGuard Home, phase C | Le filtrage DNS | Son résolveur amont suit le choix de sortie du service. | Le résolveur de la `<ISP-BOX>`, qui ferait quitter le tailnet |
| ntfy, phase D | Les notifications | Une alerte signale une coupure de l'anonymiseur. Une autre alerte signale une coupure de courant. | Aucune |
| Un disque exportable | Le stockage | La redondance sera décidée quand le disque contiendra des données précieuses. | La redondance immédiate |
| Images épinglées par digest | La reproductibilité | N'utilisez jamais `latest` sans vérification. | Les images flottantes |
| `tailscaled` compagnon, phase C | Donner une adresse Tailscale à chaque service | La bascule se fait avec `tailscale set`. Elle ne recrée pas le conteneur. | Aucune |

## Les décisions actées

Le tableau ci-dessous liste les décisions actées. Chaque décision a une règle dans `guidelines.md`. Mettez à jour ce tableau quand une décision change.

| Domaine | Décision |
|---|---|
| Menace | Le fournisseur d'accès et les métadonnées. Le mode fast de Nym est retenu, car le mixnet est trop lent. Le géo-bypass est désactivé : le client ne doit pas signaler sa localisation au réseau Nym. |
| Sortie pour les appareils | Deux exit nodes Tailscale distincts. L'utilisateur choisit dans l'app de chaque appareil. `<OLD-SERVER-NAME>` sort en direct. `<OLD-NODE-EXIT-NYMVPN>` sort par un anonymiseur. |
| Sortie pour les microservices | Un choix par service. Le `tailscaled` du service pointe vers `<OLD-SERVER-NAME>`, vers `<OLD-NODE-EXIT-NYMVPN>`, ou vers aucun exit node. La bascule ne recrée pas le conteneur. |
| Voie 2 | Objectif confirmé du projet. L'agent choisit l'architecture et la documente. Aucune recette préexistante n'est opposable. |
| Preuve de réussite | L'adresse de sortie vue depuis l'iPhone, avec `<OLD-NODE-EXIT-NYMVPN>` sélectionné, n'est pas celle de la `<ISP-BOX>`. Ce test suffit. |
| Droits de l'agent | Écriture libre sur la voie 2. Aucun droit d'écriture sur la voie 1 sans accord de l'utilisateur. |
| Exposition | Les services restent accessibles par le tailnet seulement. Une exposition publique est une décision séparée et différée. |
| Données | Un disque exportable. La redondance sera décidée quand le disque contiendra des données précieuses. |
| Emplacement des services | Un projet compose par service dans `/opt/<service>`. Le répertoire appartient à root. Chaque projet porte son fichier `.env` de secrets, absent du repo. Le fichier `.env.example` sert de gabarit. Les images Docker sont épinglées par digest. Docker stocke les images et les volumes dans `/var/lib/docker`. |
| Méthode | Le résultat doit être fiable et sûr. L'utilisateur veut comprendre chaque mécanisme avant de continuer. |
| Modalité de travail | L'agent propose et agit. L'utilisateur garde la main sur la voie 1. |
| DNS | AdGuard Home devient un microservice. Son résolveur amont suit le choix de sortie du service. |
| Surveillance | Une alerte signale une coupure de l'anonymiseur ou une coupure de courant. Le service de notification est ntfy. |
| Repo | Le repo GitHub est privé. Il contient les compose, les configurations et cette documentation. |
| Secrets | Les secrets vivent dans `.env`. Le `.gitignore` reste strict. L'agent ne cherche jamais une clé, une graine ou un mot de passe dans les fichiers de l'utilisateur. Il n'utilise un secret que si l'utilisateur le lui donne. |
| PC gaming | Windows sert au jeu. Linux sert de nœud tailnet, de WoL et d'accès distant. |
| Accès au serveur | Le tailnet donne l'accès. Une réservation d'adresse IP sur le réseau local ne servira qu'au jour du WoL. |
