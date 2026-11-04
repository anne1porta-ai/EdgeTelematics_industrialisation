# Stratégie et cahier de tests

## Objectif

Vérifier que la collecte locale, la persistance, la synchronisation et la chaîne OTA conservent leurs résultats après une modification.

La stratégie combine :

- tests unitaires des règles GEO et Safety ;
- tests d'intégration SQLite et réseau ;
- tests de résilience et de circuit breaker ;
- tests OTA et rollback ;
- démonstrations complètes.

## Exécution

```powershell
py lancer.py tests
```

ou directement :

```powershell
py -m pytest -q
```

Résultat attendu : **55 tests réussis**.

## Répartition des tests

| Fichier | Nombre | Règles principales |
|---|---:|---|
| `tests/geo/test_geo_engine.py` | 10 | Bounding Box, Ray Casting, frontière, erreurs JSON et transition d'entrée. |
| `tests/safety/test_safety_engine.py` | 10 | seuil, lecture CSV, événements, bilan et mode sans rétention. |
| `tests/safety/test_hysteresis.py` | 4 | plateau, seuil de réarmement et émission immédiate. |
| `tests/bloc3/test_repository.py` | 3 | persistance SQLite, archivage et type d'événement. |
| `tests/bloc3/test_sync.py` | 2 | conservation sur échec et synchronisation après reprise. |
| `tests/bloc3/test_circuit_breaker.py` | 6 | états CLOSED, OPEN, HALF_OPEN et blocage des appels. |
| `tests/bloc3/test_crisis_regression.py` | 6 | traitement en flux, séparation réseau, timeout, HTTPS et idempotence. |
| `tests/bloc3/test_ota.py` | 4 | manifeste, installation, rollback et paquet altéré. |
| `tests/bloc3/test_adaptation.py` | 10 | identité stable, backoff, collecte non bloquante et conservation du bilan. |
| **Total** | **55** | |

## Critères de réussite

### GEO

- une position extérieure à la Bounding Box est rejetée ;
- une position intérieure au polygone est reconnue ;
- un point sur le contour est considéré comme intérieur ;
- une transition extérieur → intérieur produit une seule alerte.

### Safety

- le seuil `-2,5 m/s²` est strict ;
- les mesures normales ne produisent pas d'événement ;
- un plateau de mesures fortes ne produit qu'un événement avant le réarmement ;
- la lecture peut compter les événements sans les conserver dans une liste ;
- un fichier absent ou une valeur invalide provoque l'erreur attendue ;
- le dernier bilan valide est conservé lorsqu'une nouvelle analyse échoue.

### Stockage et synchronisation

- l'événement est persisté avant le réseau ;
- l'identifiant reste stable pendant les retries ;
- le backoff est enregistré dans SQLite ;
- le succès déplace l'événement vers l'historique ;
- la panne réseau ne bloque pas la collecte.

### Circuit breaker

- ouverture après trois échecs ;
- aucun appel pendant `OPEN` ;
- une sonde autorisée en `HALF_OPEN` ;
- succès : retour à `CLOSED` ;
- échec : retour à `OPEN`.

### OTA

- checksum du paquet valide ;
- paquet altéré refusé avant modification de l'état ;
- échec d'installation : version précédente conservée ;
- installation réussie : nouvelle version enregistrée.

## Vérifications avant publication

```powershell
py lancer.py tests
py lancer.py demo
py lancer.py stress
py lancer.py resilience
py lancer.py build --version demo-local
py lancer.py staging
```

Les tests et démonstrations valident les scénarios simulés. Ils ne remplacent pas un essai longue durée sur une tablette Zebra, une panne 4G réelle ou un déploiement OTA de production.
