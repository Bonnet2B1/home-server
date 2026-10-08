# Todo : les tâches restantes

Ce fichier liste ce qui reste à faire. Chaque tâche vit à un seul endroit. Le détail des faits est dans `architecture.md` ou dans `runbook.md`.

## La voie 2

La voie 2 est en service depuis le 2026-10-03. Trois tâches restent ouvertes sur elle. La première est le test final depuis l'iPhone.

- Testez la voie 2 depuis l'iPhone avec `<OLD-NODE-EXIT-NYMVPN>` sélectionné. Vérifiez ensuite que la voie 1 répond toujours avec `<OLD-SERVER-NAME>`.
- Mesurez la MTU effective sur du trafic réel. Le bug [6465](https://github.com/nymtech/nym-vpn-client/issues/6465) vise les tunnels Nym au-dessus de 1300.
- Révoquez les clés d'authentification Tailscale dans la console. La liste des clés à révoquer est dans `operations.md`.

## Les étapes communes

Ces étapes concernent les deux voies. Elles ne font partie d'aucune phase. Deux étapes restent ouvertes.

- Durcissez SSH. Le service écoute encore sur `0.0.0.0:22`. Restreignez l'écoute au tailnet après le test d'accès distant.
- Décidez du réglage `--accept-dns`. Le réglage actuel reste à `false`, car c'est le défaut du conteneur. La décision se prend le jour de la tâche AdGuard Home. Chaque service anonymisé pointera son résolveur vers `100.100.100.100`.

## Les phases restantes

Trois phases restent ouvertes. `readme.md` donne leur état global. Chaque phase a sa tâche ici.

- Ajoutez les microservices AdGuard Home et WoL. Le gabarit de la phase C est dans `architecture.md`.
- Ajoutez la surveillance et les notifications avec ntfy. Une alerte signale une coupure de l'anonymiseur. Une autre alerte signale une coupure de courant.
- Créez le repo GitHub privé et le README. Le repo contient les compose, les configurations et cette documentation.

## Les défauts connus, non corrigés

Cette section liste les défauts connus qui restent ouverts. Chaque défaut a une conséquence mesurée. Aucun d'eux n'est corrigé aujourd'hui.

- `iw reg get` renvoie `country 00: DFS-UNSET`. Tous les canaux sont en `PASSIVE-SCAN`. Le domaine réglementaire n'a jamais été posé. C'est un défaut connu avec `iwlwifi`. Pour le corriger, exécutez `iw reg set FR` avec quelqu'un sur place. La commande exige une désassociation Wi-Fi.
- `wpa_supplicant` tourne sous `supervise-daemon` avec `--respawn-max 5 --respawn-period 1800`. Au-delà de cinq redémarrages en 30 minutes, le superviseur renonce. Le serveur reste alors sans liaison Wi-Fi.
- Les résolveurs du Mac sont `100.100.100.100` et `fd7a:115c:a1e0::53`, donc MagicDNS. Toute résolution de nom dépend du tailnet, donc du Wi-Fi instable. C'est une seconde cause de « ça marche à peu près ». Le contournement consiste à garder MagicDNS et à ajouter un résolveur public en second. Rien n'a été modifié.
- Le redémarrage complet de l'hôte n'a pas été vérifié. La configuration est persistante et validée par `ifup -n`. Le gardien est au runlevel `default`. Le service `networking` continue la boucle si `eth0` échoue. Le risque est faible, mais l'essai reste à faire.

## Le conditionnel

Cette section liste les travaux qui attendent une condition. La condition est nommée pour chaque travail. Aucun de ces travaux ne bloque une autre étape.

- Mesurez le débit réel de la voie 2 contre un fichier de test. La mesure donne le plafond réel et classe les services par débit. Elle ne bloque aucune étape.
- Exposez les services publiquement seulement quand le besoin réel arrive. L'exposition demande un reverse-proxy et un domaine.
- Ajoutez la redondance du disque quand le serveur héberge une donnée précieuse. La sauvegarde attend la même condition.
- Ajoutez l'onduleur et la réservation d'adresse IP sur le réseau local le jour du WoL.
- Débranchez la nappe de la batterie. La batterie est gonflée et le châssis est déformé. Planifiez cette opération sans urgence.
- Nettoyez les images Docker inutilisées. Cette opération reste facultative.
