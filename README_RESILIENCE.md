# Démonstration Résilience

Lancer :

```powershell
.\LANCER_DEMO_CRISE.bat
```

La démonstration prouve successivement :

```text
traitement en flux sans historique RAM
-> freinage stocké dans SQLite
-> coupure 4G
-> collecte toujours active
-> retries 2 s / 4 s / 8 s
-> retour réseau
-> archivage après succès
-> timeout HTTP réel
-> idempotence côté serveur
```

La simulation est dans `run_bloc3_demo.py`. Les mécanismes réels restent dans :

- `src/safety/` ;
- `src/storage/event_repository.py` ;
- `src/sync/sync_service.py`.

Tests ciblés :

```powershell
.\LANCER_TESTS_CRISE.bat
```
