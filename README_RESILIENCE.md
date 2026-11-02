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
-> circuit OPEN après 3 échecs
-> appels réseau suspendus temporairement
-> retour réseau
-> sonde HALF_OPEN
-> circuit CLOSED après succès
-> archivage après ACK
-> timeout HTTP réel
-> idempotence côté serveur
```

## Rôle des mécanismes

```text
SQLite          : conserve les alertes
Backoff         : espace les retries d'une alerte
Circuit breaker : suspend tous les appels quand le serveur reste indisponible
```

Réglages de la démonstration :

```text
Seuil d'ouverture : 3 échecs consécutifs
Pause du circuit  : 5 secondes
Backoff SQLite    : 2 s, 4 s, 8 s...
```

La simulation de panne est dans `run_bloc3_demo.py`. Les mécanismes réels restent dans :

- `src/safety/` ;
- `src/storage/event_repository.py` ;
- `src/sync/sync_service.py` ;
- `src/sync/circuit_breaker.py`.

Tests ciblés :

```powershell
.\LANCER_TESTS_CRISE.bat
```
