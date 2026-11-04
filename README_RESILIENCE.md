# Résilience — continuer pendant une panne réseau

## Objectif

La démonstration vérifie qu'une coupure réseau ne bloque pas la collecte et ne provoque pas la perte des événements.

```powershell
py lancer.py resilience
```

Le raccourci Windows reste disponible :

```powershell
.\LANCER_DEMO_CRISE.bat
```

## Scénario démontré

```text
mesures analysées en flux
        ↓
freinage enregistré dans SQLite
        ↓
coupure réseau simulée
        ↓
retries espacés par le backoff
        ↓
circuit breaker OPEN après trois échecs
        ↓
collecte toujours active
        ↓
retour du réseau et sonde HALF_OPEN
        ↓
succès, circuit CLOSED et archivage
```

## Pourquoi chaque mécanisme est utile

| Mécanisme | Rôle dans la panne |
|---|---|
| **SQLite Store-and-Forward** | Conserver l'événement avant l'envoi. |
| **Backoff** | Éviter de retenter en boucle : 2 s, 4 s, 8 s, etc. |
| **Circuit breaker** | Suspendre temporairement les appels après plusieurs échecs. |
| **Timeout HTTP** | Empêcher un appel réseau de rester bloqué sans fin. |
| **Idempotence** | Garantir qu'un renvoi du même événement ne crée pas de doublon. |

## Réglages de la démonstration

```text
Ouverture du circuit : 3 échecs consécutifs
Pause du circuit      : 5 secondes
Backoff SQLite        : 2 s, 4 s, 8 s, etc.
```

Ces valeurs sont courtes pour rendre la démonstration visible. Elles devront être calibrées pour une exploitation réelle.

## Résultat attendu

```text
160 mesures pendant la séquence réseau
1 freinage détecté
0 événement en attente après la reprise
1 événement archivé
circuit ouvert pendant la panne puis refermé
1 stockage serveur pour 2 envois du même identifiant
```

## Ce que la démonstration prouve

- la collecte est indépendante du réseau ;
- l'événement est stocké avant l'envoi ;
- les tentatives sont espacées ;
- les appels sont suspendus quand le service reste indisponible ;
- la reprise se fait sans perdre ni dupliquer l'événement.

## Ce qui reste simulé

La coupure 4G, l'API distante et la flotte de tablettes sont simulées localement. La validation terrain devra confirmer le comportement sur une Zebra et avec un réseau mobile réel.

## Tests

```powershell
py lancer.py tests
```

La suite vérifie notamment l'ouverture du circuit, le blocage pendant `OPEN`, la sonde en `HALF_OPEN`, la reprise après succès et le retour à `OPEN` après un nouvel échec.

[Retour au Bloc 3](README_BLOC3.md) · [Architecture détaillée](docs/ARCHITECTURE_ET_RESILIENCE.md)
