# Évolution pédagogique et technique du projet

## Objectif de la mise à jour

Rendre le projet plus facile à lire, à lancer et à expliquer **sans retirer ses mécanismes d'industrialisation**.

## Ce qui a été simplifié

| Avant | Maintenant | Intérêt |
|---|---|---|
| Plusieurs commandes dispersées | Un point d'entrée `lancer.py` | Trouver rapidement la commande adaptée. |
| `dataclass` et annotations complexes dans le code applicatif | Classe simple, fonctions, boucles et conditions explicites | Rendre le Python plus accessible. |
| Chemins dépendants du dossier courant | Chemins calculés depuis la racine du projet | Lancer le projet depuis un autre dossier. |
| Écriture directe de `daily_score.json` | Écriture temporaire puis remplacement | Conserver le dernier JSON valide si l'écriture échoue. |
| Documentation dispersée | README principal, guides `docs/` et preuves Bloc 3 | Séparer la prise en main, les détails et les preuves. |

## Ce qui a été conservé

- moteurs GEO et Safety ;
- traitement en flux ;
- SQLite en mode WAL et Store-and-Forward ;
- identifiant stable pendant les retries ;
- backoff 2 s, 4 s, 8 s, etc. ;
- circuit breaker `CLOSED`, `OPEN`, `HALF_OPEN` ;
- timeout HTTP et idempotence ;
- archivage après confirmation ;
- tests de crise ;
- build, SHA-256, signature, staging, promotion et rollback OTA.

## Ce qui n'a pas été changé silencieusement

Les règles métier restent celles du projet industrialisé :

- GEO : alerte d'entrée dans le polygone ;
- Safety : seuil de détection et seuil de réarmement actuels ;
- mode stress : 1 000 mesures.

La zone buffer et l'anti-rebond temporel de 200 ms appartiennent à un autre POC. Les ajouter ici demanderait une évolution fonctionnelle séparée et une mise à jour des événements, des démonstrations et des tests.

## Validation de la version

```powershell
py lancer.py tests
py lancer.py demo
py lancer.py stress
py lancer.py resilience
py lancer.py build --version demo-local
py lancer.py staging
py lancer.py ota --mode rollout
```

Résultats attendus : 55 tests réussis, démonstrations fonctionnelles, événement conservé pendant la panne, reprise sans doublon et paquet validé en staging.

[Historique détaillé](docs/HISTORIQUE_MODIFICATIONS.md)
