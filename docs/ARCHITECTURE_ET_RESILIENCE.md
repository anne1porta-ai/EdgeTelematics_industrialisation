# Architecture et résilience

## Objectif

Le projet sépare la collecte locale du réseau afin qu'une panne 4G ne bloque pas l'analyse des capteurs.

```text
mesure capteur
    ↓
analyse locale
    ↓
événement métier
    ↓
SQLite avant le réseau
    ↓
worker de synchronisation
```

## Composants

| Composant | Rôle |
|---|---|
| `src/geo/` | Classer les positions à l'aide d'une Bounding Box puis du Ray Casting. |
| `src/safety/` | Lire les accélérations en flux et produire un événement par épisode détecté. |
| `src/domain/` | Définir les événements métier indépendamment du stockage et du réseau. |
| `src/storage/` | Conserver les alertes en attente et l'historique synchronisé dans SQLite. |
| `src/sync/` | Envoyer les alertes, programmer les retries et protéger l'API avec un circuit breaker. |
| `src/ota/` | Vérifier les paquets et simuler une installation ou un rollback. |

## Traitement en flux

Les mesures d'accéléromètre sont traitées une par une. Le programme ne conserve pas tout le signal en mémoire. Quand un événement est détecté, il est transformé en `TelemetryEvent` puis enregistré dans SQLite.

Le fichier `daily_score.json` est écrit dans un fichier temporaire, puis remplacé uniquement lorsque le nouveau JSON est complet. Une interruption pendant l'écriture ne remplace donc pas le dernier bilan valide par un fichier partiel.

## Store-and-Forward

L'événement est enregistré avant tout appel réseau :

```text
1. création d'un identifiant UUID
2. écriture dans pending_alerts
3. tentative d'envoi
4. succès : archivage dans event_history
5. échec : conservation et programmation d'un nouvel essai
```

L'identifiant reste le même pendant les retries et est envoyé dans l'en-tête `Idempotency-Key`.

## Backoff et circuit breaker

Ces deux mécanismes répondent à des problèmes différents.

| Mécanisme | Rôle |
|---|---|
| **Backoff** | Espacer les nouvelles tentatives d'une alerte : 2 s, 4 s, 8 s, etc. |
| **Circuit breaker** | Suspendre tous les appels quand le service distant reste indisponible. |

Le circuit breaker suit trois états :

```text
CLOSED
  ↓ 3 échecs consécutifs
OPEN
  ↓ délai de reprise
HALF_OPEN
  ├─ succès → CLOSED
  └─ échec  → OPEN
```

Pendant l'état `OPEN`, la collecte et l'enregistrement SQLite continuent.

## Démonstration de résilience

La commande suivante lance le scénario complet :

```powershell
py lancer.py resilience
```

Le scénario montre :

1. 10 000 mesures traitées sans historique du signal en RAM ;
2. un freinage persisté avant l'envoi ;
3. une coupure réseau simulée ;
4. les retries 2 s, 4 s et 8 s ;
5. l'ouverture du circuit après trois échecs ;
6. la reprise via `HALF_OPEN` ;
7. l'archivage après succès ;
8. un timeout HTTP réel sur une API locale ;
9. l'idempotence avec deux envois du même identifiant.

Le bilan attendu de la séquence réseau est :

```text
160 mesures
1 freinage
0 alerte en attente
1 alerte synchronisée dans l'historique
```

## Ce qui est réel et ce qui est simulé

**Réel dans le code :** traitement en flux, SQLite, backoff, circuit breaker, timeout HTTP, clé d'idempotence et archivage.

**Simulé dans la démonstration :** coupure 4G, serveur distant, capteurs réels et conditions terrain.

## Choix conservés dans cette livraison

Cette réorganisation ne modifie pas les algorithmes métier :

- GEO : Bounding Box + Ray Casting, alerte lors du passage extérieur vers intérieur ;
- Safety : seuil `-2,5 m/s²` et réarmement au-dessus de `-2,3 m/s²` ;
- stress : 1 000 mesures simulées ;
- synchronisation : Store-and-Forward, backoff et circuit breaker existants.
