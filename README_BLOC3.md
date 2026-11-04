# Bloc 3 — Industrialisation, résilience et déploiement

## Ce que ce projet démontre

Le projet part des moteurs GEO et Safety, puis ajoute les mécanismes nécessaires pour exploiter leurs événements dans une solution plus robuste.

```text
capteurs simulés
      ↓
moteurs GEO et Safety
      ↓
événement métier
      ↓
SQLite avant le réseau
      ↓
worker de synchronisation
      ↓
API distante
```

**Principe essentiel : la collecte et la détection restent locales.** Une coupure réseau ne doit donc ni arrêter les capteurs, ni faire perdre les événements déjà détectés.

## Les mécanismes du Bloc 3

| Mécanisme | Valeur apportée | Preuve dans le projet |
|---|---|---|
| **Traitement en flux** | Analyser les mesures une par une sans conserver tout le signal en mémoire. | `py lancer.py stress` |
| **Store-and-Forward SQLite** | Enregistrer un événement avant de tenter son envoi. | `src/storage/event_repository.py` |
| **Backoff** | Espacer les nouvelles tentatives : 2 s, 4 s, 8 s, etc. | Démonstration de résilience |
| **Circuit breaker** | Suspendre les appels réseau quand le service reste indisponible. | États `CLOSED`, `OPEN`, `HALF_OPEN` |
| **Idempotence** | Éviter qu'un même événement renvoyé soit enregistré deux fois. | En-tête `Idempotency-Key` |
| **CI/CD et OTA** | Construire, contrôler, signer, tester puis promouvoir le même paquet. | Workflows GitHub et scripts de staging |

## Store-and-Forward, en français simple

Le programme suit cet ordre :

```text
1. détecter l'événement
2. l'enregistrer dans SQLite
3. tenter l'envoi
4. en cas d'échec, le garder et programmer un nouvel essai
5. après confirmation, l'archiver dans l'historique
```

L'identifiant de l'événement reste stable pendant les retries. Le serveur peut ainsi reconnaître un renvoi et éviter un doublon.

## Backoff et circuit breaker : deux rôles différents

| Mécanisme | Question à laquelle il répond |
|---|---|
| **Backoff** | « Quand faut-il retenter cet événement ? » |
| **Circuit breaker** | « Faut-il encore appeler le service distant maintenant ? » |

Le circuit breaker fonctionne ainsi :

```text
CLOSED
  ↓ trois échecs consécutifs
OPEN
  ↓ délai de reprise
HALF_OPEN
  ├─ succès → CLOSED
  └─ échec  → OPEN
```

Pendant l'état `OPEN`, la collecte et l'écriture dans SQLite continuent.

## Commandes de preuve

```powershell
py lancer.py demo
py lancer.py stress
py lancer.py resilience
py lancer.py tests
py lancer.py build --version demo-local
py lancer.py staging
py lancer.py ota --mode rollout
```

### Résultats attendus

- **55 tests réussis** ;
- 1 entrée ZFE et 1 freinage dans la démonstration standard ;
- 1 000 mesures traitées en mode stress ;
- collecte maintenue pendant la panne ;
- 0 événement en attente après la reprise ;
- 1 événement archivé ;
- circuit ouvert pendant la panne puis refermé ;
- timeout HTTP déclenché ;
- un seul stockage serveur pour deux envois du même identifiant ;
- paquet vérifié en staging puis rollback simulé si nécessaire.

## Ce qui est réel et ce qui est simulé

**Réel dans le code :** SQLite, traitement en flux, retries, backoff, circuit breaker, timeout, idempotence, build ZIP, SHA-256, signature CI, staging et réutilisation du même artefact.

**Simulé pour la démonstration :** capteurs physiques, coupure 4G réelle, serveur de production, installation Android, MDM et déploiement OTA sur une flotte de Zebra.

## Documents associés

- [Résilience](README_RESILIENCE.md)
- [Déploiement CI/CD et OTA](README_DEPLOIEMENT.md)
- [Démonstration CI/CD](CI_CD_DEMO.md)
- [Guide Dossiers 4 et 5](README_DOSSIERS_4_5.md)
- [Validation finale](VALIDATION.txt)
- [Architecture détaillée](docs/ARCHITECTURE_ET_RESILIENCE.md)
