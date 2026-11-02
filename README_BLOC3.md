# Bloc 3 — Industrialisation du POC Edge

## Objectif

Le pilote a révélé deux causes principales :

- les mesures étaient accumulées dans une liste globale ;
- l'appel réseau était exécuté dans la boucle de collecte.

La correction conserve Python et sépare trois responsabilités :

```text
collecte en flux -> SQLite -> worker réseau
```

## 1. Collecte sans accumulation en mémoire

`run_demo.py` transmet les mesures au moteur Safety une par une.

```text
lecture d'une mesure
-> analyse
-> alerte éventuelle
-> mesure oubliée
```

Aucun historique de mesures n'est conservé en RAM. Seules les alertes utiles sont enregistrées dans SQLite.

Le mode stress traite 1 000 mesures avec :

```powershell
python run_demo.py --stress
```

## 2. Evénements métier

`src/domain/telemetry_event.py` définit un modèle simple :

```python
@dataclass(frozen=True)
class TelemetryEvent:
    event_type: str
    payload: dict[str, Any]
```

Deux types sont utilisés :

- `harsh_braking` ;
- `zfe_entry`.

Le `timestamp` vient du capteur. SQLite ajoute ensuite `captured_at`, l'heure de l'enregistrement local.

## 3. Store-and-Forward SQLite

`src/storage/event_repository.py` fournit :

| Fonction | Rôle |
|---|---|
| `initialize_database()` | Créer la file et l'historique. |
| `save_alert(event)` | Enregistrer un `TelemetryEvent` avant le réseau. |
| `get_pending_alerts()` | Lire les alertes prêtes à être envoyées. |
| `schedule_retry()` | Enregistrer le prochain essai : 2, 4, 8 secondes... |
| `mark_alert_synced()` | Archiver après succès puis retirer de la file active. |

L'UUID est créé une seule fois et réutilisé pendant les retries.

## 4. Worker réseau

`src/sync/sync_service.py` contient uniquement le mécanisme réel :

```text
lire SQLite
-> envoyer
-> échec : programmer un retry
-> succès : archiver
```

La panne simulée n'est plus dans ce fichier. Elle est définie dans `run_bloc3_demo.py` puis injectée au worker avec une fonction `sender`.

L'appel HTTP réel utilise :

- `Authorization` ;
- `Idempotency-Key` ;
- `timeout=(3, 10)`.

Il n'y a pas de circuit breaker dans ce POC.

## 5. Démonstration de crise

Lancer :

```powershell
.\LANCER_DEMO_CRISE.bat
```

La démonstration montre :

1. 10 000 mesures traitées en flux, sans historique RAM ;
2. un freinage enregistré dans SQLite ;
3. une coupure 4G pendant laquelle la collecte continue ;
4. le backoff 2 s, 4 s, 8 s ;
5. le retour du réseau ;
6. l'archivage après succès ;
7. un timeout HTTP réel ;
8. l'idempotence `STORED` puis `DUPLICATE`.

Bilan attendu :

```text
160 mesures de la séquence réseau
1 freinage
0 alerte en attente
1 alerte synchronisée dans l'historique
```

## 6. Tests de crise

```powershell
.\LANCER_TESTS_CRISE.bat
```

Les six preuves sont :

- pas d'accumulation des mesures ;
- aucun appel réseau dans la collecte ;
- persistance avant envoi ;
- conservation et retry après échec ;
- archivage après succès ;
- HTTPS, authentification, idempotence et timeout.

Suite complète :

```powershell
.\LANCER_TESTS.bat
```

## 7. CI/CD et OTA

Le workflow GitHub exécute :

```text
Ruff -> mypy -> pytest -> Bandit -> pip-audit -> Gitleaks
-> build -> SHA-256 -> signature -> staging
```

Le même artefact validé est ensuite récupéré par le workflow manuel de promotion, sans reconstruction.
