# Modifications appliquées à la dernière version

## Simplification du code

- suppression du buffer `deque(maxlen=600)` ;
- traitement des mesures une par une ;
- aucune liste globale de mesures ;
- simulation réseau sortie de `src/sync/sync_service.py` ;
- worker configurable avec une fonction d'envoi simple ;
- `save_alert()` accepte uniquement `TelemetryEvent` ;
- suppression de l'ancien alias `delete_alert()` ;
- confirmation unique avec `mark_alert_synced()` ;
- suppression de la date `created_at` du modèle métier ;
- conservation de `timestamp` pour la mesure et `captured_at` pour SQLite ;
- suppression des anciennes fonctions Safety basées sur des listes ;
- découpage de la démonstration en fonctions courtes ;
- suppression des copies du projet présentes dans `scripts/` ;
- suppression des caches Python et du lanceur Windows dupliqué.

## Fonctionnalités conservées

- Geo/ZFE ;
- détection Safety avec hystérésis ;
- mode stress ;
- SQLite WAL ;
- Store-and-Forward ;
- backoff 2, 4, 8 secondes ;
- circuit breaker CLOSED / OPEN / HALF_OPEN ;
- timeout HTTP ;
- idempotence ;
- historique `synced=1` ;
- tests de crise ;
- build, SHA-256, signature, staging, promotion et rollback OTA.

## Démonstration

La première preuve n'affiche plus un buffer à 600/600. Elle affiche :

```text
10 000 mesures traitées
0 historique de mesures en RAM
traitement une mesure à la fois
```

La séquence réseau conserve :

```text
160 mesures
1 freinage
backoff 2 s -> 4 s -> 8 s
0 alerte en attente
1 alerte archivée
```

## Circuit breaker ajouté

- ouverture après 3 échecs réseau consécutifs ;
- suspension des appels pendant 5 secondes dans la démo ;
- une seule sonde en état HALF_OPEN ;
- fermeture après succès ;
- réouverture si la sonde échoue ;
- collecte et stockage SQLite inchangés pendant l'ouverture.
