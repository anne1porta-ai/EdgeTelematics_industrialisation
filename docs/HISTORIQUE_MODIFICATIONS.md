# Historique des modifications et validation

## Simplification appliquée avant cette livraison

- suppression de l'ancien buffer `deque(maxlen=600)` ;
- traitement des mesures une par une ;
- suppression des listes globales de mesures ;
- simulation réseau retirée du worker réel ;
- fonction d'envoi injectable dans le worker ;
- `save_alert()` limité aux `TelemetryEvent` ;
- archivage centralisé dans `mark_alert_synced()` ;
- distinction entre le `timestamp` métier et `captured_at` SQLite ;
- démonstration découpée en fonctions ;
- ajout du circuit breaker et de ses états.

## Fonctionnalités conservées

- moteur GEO ;
- moteur Safety avec hystérésis ;
- mode stress à 1 000 mesures ;
- SQLite WAL et Store-and-Forward ;
- backoff 2, 4, 8 secondes ;
- circuit breaker `CLOSED`, `OPEN`, `HALF_OPEN` ;
- timeout HTTP ;
- clé d'idempotence ;
- historique `synced=1` ;
- tests de crise ;
- build, SHA-256, signature, staging, promotion et rollback OTA.

## Améliorations de cette mise à jour

- nouveau point d'entrée `lancer.py` ;
- documentation consolidée dans `docs/` ;
- suppression des README redondants après fusion de leur contenu ;
- chemins de données indépendants du dossier depuis lequel la commande est lancée ;
- configuration explicite du fichier SQLite et de l'API ;
- retour du bilan par `run_safety_engine()` ;
- écriture atomique de `daily_score.json` ;
- clarification entre la signature pédagogique historique et la signature CI ;
- correction de la commande de génération des clés OTA ;
- commentaires et docstrings harmonisés sur les composants principaux.
- suppression de `@dataclass` et des annotations de types complexes dans le code applicatif ;
- remplacement des compréhensions et expressions compactes par des boucles et des étapes explicites ;
- simplification des accès SQLite, du worker réseau, du build et de la simulation OTA, sans retirer leurs fonctions ;
- ajout d’un parcours de lecture dans le README pour comprendre le code progressivement.

## Validation de référence

Commandes :

```text
python -m pytest -q
python run_bloc3_demo.py --data-dir resultats_demo
python run_demo.py --stress
python -m scripts.build_package --version demo-local
python -m scripts.staging_demo --manifest dist/manifest.json --output-dir staging
python scripts/demo_ota_rollout.py --mode rollout
```

Résultats attendus :

- 10 000 mesures traitées sans historique du signal en RAM ;
- 160 mesures pendant la séquence de panne ;
- 1 freinage ;
- 0 alerte en attente après reprise ;
- 1 alerte dans `event_history` ;
- circuit ouvert pendant la panne puis refermé ;
- timeout observé ;
- un seul stockage pour deux envois du même identifiant ;
- **55 tests réussis**.

## Périmètre

Cette mise à jour ne porte pas la zone buffer ni l'anti-rebond temporel de 200 ms du POC pédagogique plus récent. Ces évolutions changeraient les règles métier et nécessiteraient un chantier séparé sur les événements, les démonstrations et les tests.
