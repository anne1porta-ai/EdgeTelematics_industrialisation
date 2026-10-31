# Bloc 3 — Industrialisation GreenMove Edge

Cette branche conserve les réalisations du Bloc 2 et ajoute les mécanismes nécessaires à l’industrialisation du POC GreenMove Edge.

Branche de travail :

`bloc3-industrialisation`

## 1. Contexte

Le pilote réalisé sur 50 véhicules a permis d’identifier plusieurs limites du POC initial avant un passage à l’échelle de 5 000 tablettes.

Les principales causes identifiées dans le code de l’Annexe 1 sont :

- utilisation d’un `data_buffer` global non borné ;
- appel réseau synchrone directement dans la boucle métier ;
- absence de timeout et de gestion d’erreur réseau ;
- absence de stockage local robuste ;
- absence de mécanisme de reprise après coupure réseau ;
- clé API présente en clair dans l’URL ;
- observabilité et tests insuffisants.

Le passage de 50 à 5 000 véhicules multiplie par 100 l’exposition à ces défauts. L’objectif du Bloc 3 est donc de corriger les causes racines avant toute généralisation.

## 2. Choix d’architecture

Le projet conserve Python et refactorise l’architecture existante au lieu de réécrire l’ensemble en C++ ou Rust.

Ce choix est motivé par :

- une deadline fixe de 4 mois ;
- les compétences Python déjà présentes dans l’équipe ;
- la volonté de préserver la logique métier et les réalisations du Bloc 2 ;
- des causes de panne principalement architecturales et non liées aux performances intrinsèques du langage ;
- le risque supplémentaire qu’introduirait une réécriture complète.

L’architecture Bloc 3 ajoute les couches suivantes :

- `src/domain` : événements métier indépendants de l’infrastructure ;
- `src/storage` : persistance locale SQLite ;
- `src/sync` : synchronisation différée avec timeout et retry ;
- `src/ota` : validation de package, simulation de mise à jour et rollback ;
- `tests/bloc3` : tests de non-régression du périmètre Bloc 3.

Les modules `geo` et `safety` du Bloc 2 sont conservés.

## 3. Persistance locale

`EventRepository` remplace le buffer mémoire non borné du POC initial.

Les événements sont écrits dans SQLite avec un statut `synced`.

Tant qu’un événement n’a pas été transmis avec succès, il reste disponible localement et pourra être rejoué lors du retour du réseau.

## 4. Synchronisation différée

`SyncService` découple le transport réseau du traitement métier.

Le service :

- récupère les événements non synchronisés ;
- limite le nombre d’événements traités par lot ;
- applique un timeout transmis au transport ;
- effectue plusieurs tentatives ;
- intercepte les erreurs réseau attendues ;
- marque un événement comme synchronisé uniquement après succès.

Une coupure 4G ne provoque donc plus la perte de la donnée.

## 5. Démonstration réseau

Commande :

```bash
python run_bloc3_demo.py
```

Résultat attendu :

```text
[LOCAL] pending before sync=1
[OFFLINE] synced=0 failed=1 pending=1
[SYNC] sent id=1 type=harsh_braking timeout=2.0s
[ONLINE] synced=1 failed=0 pending=0
```

La première tentative simule une coupure réseau.

L’événement reste localement en attente.

La seconde tentative simule le retour du réseau et permet sa synchronisation.

## 6. Tests automatisés

Tests Bloc 3 :

```bash
python -m pytest -q tests/bloc3
```

Résultat attendu :

```text
7 passed
```

Suite complète du projet :

```bash
python -m pytest -q
```

État validé avant la vidéo :

```text
27 passed
```

Les tests couvrent notamment :

- persistance locale ;
- marquage des événements synchronisés ;
- conservation des événements en cas de panne réseau ;
- reprise après retour du réseau ;
- validation du manifest OTA ;
- mise à jour réussie ;
- rollback après échec d’installation.

## 7. Intégration continue

Le workflow GitHub Actions se trouve dans :

`.github/workflows/bloc3-ci.yml`

Il est déclenché sur :

- push sur `bloc3-industrialisation` ;
- Pull Request.

Le workflow réalise automatiquement :

1. checkout du dépôt ;
2. installation de Python ;
3. installation des dépendances ;
4. exécution de la suite de tests ;
5. validation du manifest OTA.

Si les tests échouent, les étapes suivantes ne sont pas validées.

Le workflow constitue aujourd’hui la partie CI de la chaîne.

La chaîne cible complète de production est :

`Commit → Pull Request → Tests → Build → Staging → Release progressive`

## 8. Validation OTA

Commande :

```bash
python -m src.ota.check_manifest
```

Résultat attendu :

```text
[OTA] manifest version=2.3.0 signature=valid checksum=valid
```

Le checksum SHA-256 vérifie réellement l’intégrité du package.

La `demo_signature` est volontairement pédagogique.

Elle ne constitue pas une signature cryptographique de production.

Dans une architecture industrielle, elle serait remplacée par une signature asymétrique avec :

- clé privée protégée côté backend ;
- clé publique embarquée sur les tablettes.

## 9. Mise à jour et rollback

Simulation d’une mise à jour réussie :

```bash
python -m src.ota.simulate_update --version 2.3.0
```

Simulation d’un échec d’installation :

```bash
python -m src.ota.simulate_update --version 2.4.0 --fail-install
```

Lecture du statut :

```bash
cat ota_status.json
```

Résultat attendu après échec :

```json
{
  "status": "rolled_back",
  "attempted_version": "2.4.0",
  "current_version": "2.3.0",
  "previous_version": "2.3.0"
}
```

Cette simulation illustre le principe de retour à la dernière version saine.

Elle ne constitue pas encore un updater Android de production ni une installation atomique au niveau du système d’exploitation.

## 10. Déploiement progressif cible

Le déploiement à 5 000 tablettes ne doit jamais être réalisé directement à 100 %.

Stratégie proposée :

1. canary : 1 % ;
2. pilote élargi : 10 % ;
3. ramp-up : 50 % ;
4. généralisation : 100 % uniquement si les indicateurs restent au vert.

Exemples de gates :

- taux de succès OTA suffisant ;
- stabilité du crash rate ;
- absence de perte de données ;
- remontée correcte des statuts ;
- logs exploitables.

Le seuil de 98 % présenté dans le support vidéo est une règle opérationnelle proposée pour la démonstration et non une valeur imposée par l’énoncé.

## 11. Procédure de rollback

En cas de bug majeur post-déploiement :

1. arrêter immédiatement le rollout ;
2. empêcher les nouveaux équipements de recevoir la version défectueuse ;
3. réactiver la dernière version saine N-1 ;
4. remonter le statut de rollback ;
5. journaliser l’incident ;
6. ouvrir un post-mortem ;
7. ajouter un test de non-régression avant toute nouvelle tentative.

## 12. Méthode d’investigation

Méthode utilisée :

`Reproduire → Observer → Isoler → Identifier la cause racine → Corriger → Ajouter un test de non-régression`

Chaque incident significatif doit produire une amélioration durable :

- correction de code ;
- test automatisé ;
- règle de CI ;
- procédure opérationnelle ;
- amélioration du monitoring.

## 13. Commandes de démonstration vidéo

```bash
git branch --show-current
python -m pytest -q tests/bloc3
python run_bloc3_demo.py
python -m src.ota.check_manifest
python -m src.ota.simulate_update --version 2.3.0
python -m src.ota.simulate_update --version 2.4.0 --fail-install
cat ota_status.json
```

## 14. Limites du POC Bloc 3

Le dépôt démontre les principes d’industrialisation attendus pour l’épreuve.

Il ne prétend pas implémenter complètement :

- un backend OTA de production ;
- une PKI ou une signature asymétrique réelle ;
- un updater Android atomique ;
- une supervision de flotte complète ;
- un déploiement automatique vers 5 000 équipements.

Ces éléments constituent l’architecture cible décrite dans la vidéo.