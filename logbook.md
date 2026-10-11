

## La publication du dépôt, 2026-10-11

Le dépôt est passé de privé à public. Le compte GitHub et le pseudonyme d'écriture sont conservés. La licence est MIT, au nom de `Eli`. L'adresse est <https://github.com/Bonnet2B1/home-server>.

La décision reprise de `philosophy.md` — « Le repo GitHub est privé. Il contiendra `tailscale-nym/`, `adguard/` et cette documentation. » — est dépassée sur deux points. Le dépôt est public. Le dossier `tailscale-nym/` est devenu `exit-nymvpn/` le 2026-10-10.

### Le masquage avant publication

Les valeurs qui identifient l'utilisateur ou son réseau ne sont pas publiées en clair. Chacune est remplacée par un jeton stable, défini dans `sanitize.map`. Ce fichier est ignoré par Git : il ne suit pas le dépôt.

Un filtre Git fait la conversion dans les deux sens. Au commit, `redact` remplace les valeurs réelles par les jetons. À la récupération des fichiers, il fait l'inverse. L'arbre de travail garde donc les valeurs réelles. Un hook `pre-commit` refuse un commit dont l'index contient une valeur sensible. Il refuse aussi un jeton écrit en prose sans backticks. Les règles sont dans [guidelines.md](guidelines.md), section « Le masquage avant publication ».

### L'anonymisation de l'historique

Les vingt-quatre commits d'origine ont été réécrits : contenu, auteur et message. Les dates d'auteur et de commiteur sont conservées. Tous les commits portent l'identité `Eli <eli@users.noreply.github.com>`, qui remplace l'adresse personnelle d'origine.

Les sommes de contrôle de tous les commits changent. L'historique d'origine ne subsiste que dans une sauvegarde locale. Les refs internes de l'agent contenaient l'historique non anonymisé. Elles ont été supprimées, avec le reflog et les objets orphelins, avant la publication. Seule `main` a été poussée.

### Les pseudonymes

Le compte GitHub et le pseudonyme d'écriture sont distincts. Le nom du tailnet figure dans l'URL du dépôt. Il est donc public, et le masquer n'ajouterait rien. Il reste en clair dans la documentation. Le domaine du tailnet reste masqué.

Le nom seul ne donne aucun accès. Rejoindre le tailnet demande une invitation. MagicDNS ne répond pas hors du tailnet. Aucun service n'est exposé publiquement.

### Le rendu sur GitHub

Deux effacements ont été constatés au rendu. Un jeton écrit en prose est traité comme du HTML brut et disparaît. Un jeton dans un diagramme est pris pour une balise et disparaît aussi. Les entités HTML ne sauvent rien dans un fichier Markdown : le rendu Markdown échappe le caractère `&` avant de passer le bloc à Mermaid.

Le schéma d'`architecture.md` était dessiné à la main, en largeur fixe. Le masquage a décalé ses cadres. Il a été remplacé par un diagramme Mermaid, rendu par GitHub, avec les jetons entre guillemets.

### Le dépôt public

Le dépôt contient trente commits et trente-deux fichiers. Un clone neuf du dépôt public ne contient aucune valeur masquée, dans les arbres comme dans les messages de commit. Il n'expose que `main`. Les étapes et les critères ont été inscrits dans [todo.md](todo.md) avant le travail, puis retirés une fois vérifiés, conformément au cheminement d'une modification défini dans [guidelines.md](guidelines.md).
