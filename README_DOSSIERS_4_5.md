# Dossiers 4 et 5 — Ce qu'il faut montrer

## Dossier 4 — POC fonctionnel

Le Dossier 4 vérifie que les moteurs produisent les bons événements à partir des données fournies.

| Action | Commande | Preuve attendue |
|---|---|---|
| Démonstration standard | `py lancer.py demo` | 1 entrée ZFE et 1 freinage à `-3,45 m/s²`. |
| Jeu plus volumineux | `py lancer.py stress` | 1 000 mesures traitées en flux, 1 freinage attendu. |
| Non-régression | `py lancer.py tests` | 55 tests réussis. |

### À expliquer

- la Bounding Box écarte rapidement les positions éloignées ;
- le Ray Casting vérifie l'appartenance au polygone ;
- les accélérations sont lues une par une ;
- un événement métier est créé puis enregistré dans SQLite.

## Dossier 5 — Industrialisation et résilience

Le Dossier 5 montre que la solution continue à fonctionner lorsque le réseau devient indisponible et qu'une version peut être déployée de façon contrôlée.

| Action | Commande | Preuve attendue |
|---|---|---|
| Résilience réseau | `py lancer.py resilience` | collecte active, événement conservé, circuit ouvert puis refermé. |
| Build | `py lancer.py build --version demo-local` | paquet ZIP et manifeste SHA-256. |
| Staging | `py lancer.py staging` | paquet exécuté, rollback simulé puis installation réussie. |
| Rollout OTA | `py lancer.py ota --mode rollout` | déploiement par vagues et retour à N-1 en cas de NO-GO. |

### À expliquer

1. **Store-and-Forward** : enregistrer avant d'envoyer.
2. **Backoff** : espacer les retries d'un événement.
3. **Circuit breaker** : suspendre les appels lorsque le service reste indisponible.
4. **Idempotence** : éviter un doublon lors d'un renvoi.
5. **Artefact unique** : tester puis promouvoir le même paquet.
6. **Rollback** : revenir à la version précédente si la stabilité se dégrade.

## Proposition de déroulé oral

```text
1. Montrer le POC standard.
2. Provoquer la panne réseau simulée.
3. Montrer SQLite et la collecte toujours active.
4. Montrer l'ouverture puis la fermeture du circuit.
5. Expliquer le timeout et l'idempotence.
6. Construire le paquet et montrer le manifeste.
7. Exécuter le staging puis le rollout OTA simulé.
```

## Nuance à conserver

Les preuves sont réelles au niveau du code et des fichiers produits. La coupure 4G, l'installation Android et la flotte de Zebra restent simulées ; elles devront être validées sur le terrain.

[Vue d'ensemble Bloc 3](README_BLOC3.md) · [Guide de démonstration détaillé](docs/DEMONSTRATION.md)
