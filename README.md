# EdgeTelematics Industrialisation — POC Bloc 3

Ce dépôt conserve les moteurs **Geo** et **Safety** du POC et ajoute les protections nécessaires pour démontrer la résilience et la livraison OTA.

Le code reste volontairement simple : fonctions courtes, SQLite direct, un worker réseau et des tests pytest lisibles.

## Fonctionnalités

- détection des entrées en ZFE ;
- détection d'un épisode de freinage brusque ;
- mémoire bornée avec `deque(maxlen=600)` ;
- mode stress sur 1 000 mesures ;
- alertes structurées avec `TelemetryEvent` ;
- stockage SQLite avant l'envoi ;
- Store-and-Forward avec backoff `2 s, 4 s, 8 s...` ;
- timeout HTTP et clé d'idempotence ;
- archivage des événements synchronisés avec `synced=1` ;
- démonstration de panne 4G, reprise, timeout et anti-doublon ;
- build, hash, signature, staging et promotion OTA via GitHub Actions.

## Installation Windows

```powershell
.\INSTALLER.bat
```

## Démonstrations

### Résilience

```powershell
.\LANCER_DEMO_CRISE.bat
```

La démo montre :

```text
mémoire 600/600
→ panne 4G
→ collecte toujours active
→ alerte conservée dans SQLite
→ backoff 2 s / 4 s / 8 s
→ retour réseau
→ ACK
→ file active vide
→ historique synced=1
→ timeout HTTP
→ idempotence STORED / DUPLICATE
```

### Six tests liés à la crise

```powershell
.\LANCER_TESTS_CRISE.bat
```

### Suite complète

```powershell
.\LANCER_TESTS.bat
```

### Mode stress

```powershell
.\.venv\Scripts\python.exe run_demo.py --stress
```

### Build et staging locaux

```powershell
.\LANCER_LIVRAISON.bat
```

## Structure utile

```text
src/domain/telemetry_event.py       événement métier simple
src/safety/                         collecte et freinage
src/geo/                            détection ZFE
src/storage/event_repository.py     file SQLite et historique
src/sync/sync_service.py            envoi et retry
src/ota/                            contrôle et rollback simulé
scripts/                            build, staging, clés et vagues OTA
tests/                              tests Geo, Safety et Bloc 3
.github/workflows/                  CI et promotion OTA
```

## CI/CD GitHub

Le workflow `Bloc 3 CI` exécute :

```text
Ruff + mypy
→ pytest
→ Bandit + pip-audit + Gitleaks
→ build du ZIP
→ SHA-256
→ signature
→ staging du même paquet
→ greenmove-validated-package
```

Le workflow `Promotion OTA - Demo` récupère **le même artefact**, vérifie de nouveau le hash et la signature, puis simule les vagues OTA et le rollback N-1.

## Documentation

- [README_BLOC3.md](README_BLOC3.md) : fonctionnement technique ;
- [CI_CD_DEMO.md](CI_CD_DEMO.md) : démonstration GitHub ;
- [MODIFICATIONS.md](MODIFICATIONS.md) : changements de cette version ;
- [VALIDATION.txt](VALIDATION.txt) : résultats de validation ;
- [README_ORIGINAL.md](README_ORIGINAL.md) : documentation historique conservée.

## Limites

Le POC simule les capteurs, la 4G, l'installation sur tablette et les vagues de flotte. Il ne remplace pas les essais sur Zebra réelle, la zone blanche, le reboot matériel ni l'endurance de 8 heures.
