> **Lecture courte :** [MODIFICATIONS.md](MODIFICATIONS.md) explique comment lancer le projet et suivre les fonctions reprises du PowerPoint. Les sections 3 à 6 ci-dessous décrivent le code et la démonstration actuels.

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

Les fonctions de `src/storage/event_repository.py` reprennent le principe montré dans le PowerPoint : **enregistrer l’alerte avant toute tentative d’envoi**.

`initialize_database()` prépare la table SQLite `pending_alerts`. Elle contient l’identifiant `alert_id`, le contenu `payload`, la date `created_at`, le nombre d’essais `attempts` et l’échéance `next_attempt_at`.

| Fonction | Rôle |
|---|---|
| `save_alert(sample)` | Créer l’identifiant de l’alerte, ajouter sa date de capture et valider son écriture en SQLite. |
| `get_pending_alerts()` | Relire un lot d’alertes dont l’échéance de reprise est atteinte. |
| `pending_count()` | Compter toutes les alertes conservées, y compris celles qui attendent leur prochain essai. |
| `delete_alert(alert_id)` | Supprimer l’alerte après un envoi réussi. |

L’identifiant et le contenu sont relus depuis SQLite lors d’un nouvel essai : l’alerte n’est pas recréée à chaque tentative.

Le JSON contient aussi un type explicite repris du modèle d’origine : `event_type="harsh_braking"` pour un freinage, ou `event_type="zfe_entry"` pour une entrée en ZFE. Ce champ accompagne l’alerte dans SQLite et lors de l’envoi.

## 4. Collecte et envoi dans deux parcours distincts

Dans le **thread principal**, `acquisition_loop()` appelle le moteur Safety existant avec `on_event=save_alert`. Safety lit les mesures, détecte le freinage et appelle directement la fonction de stockage. Il ne fait aucun appel HTTP dans cette collecte. Dans la démonstration, le paramètre `samples` transmet à Safety le flux cadencé de `sensor_samples()` ; la détection n’est pas réimplémentée dans le scénario.

Un seul **thread réseau** exécute `network_worker()`. Son déroulement est simple :

1. Relire les alertes disponibles avec `get_pending_alerts()`.
2. Tenter l’envoi avec `send_alert()`.
3. En cas d’échec réseau, appeler `schedule_retry(alert_id, attempts)` et conserver l’alerte.
4. En cas de succès, appeler `delete_alert(alert_id)`.

`schedule_retry()` enregistre en SQLite le compteur d’essais et la prochaine échéance. Les délais augmentent : **2, 4, 8 secondes… jusqu’à 300 secondes**. Ils restent enregistrés si le programme est arrêté puis relancé. L’attente réseau reste séparée du traitement Safety.

Ce mécanisme est une reprise avec délai croissant (*backoff*). **Il ne comporte pas de circuit breaker.** Hors simulation, `send_alert()` utilise l’appel HTTP avec `timeout=(3, 10)` ; une réponse HTTP 2xx est considérée comme un succès d’envoi.

## 5. Démonstration réseau

Depuis la racine du projet :

```bash
python run_bloc3_demo.py --data-dir resultats_demo
```

**SQLite est réel ; le réseau est simulé.** Le scénario est automatique et dure environ dix secondes. Il utilise le moteur Safety existant, avec une collecte dans le thread principal et un seul thread réseau.

1. `sensor_samples()` fournit **100 mesures à une cadence d’environ 100 ms**. Les dix premières viennent du CSV original et contiennent un seul freinage. Les suivantes sont normales (`acc_y=0`) pour continuer la collecte sans recréer de freinage.
2. Alors que la 4G simulée est coupée, Safety détecte le freinage et appelle `save_alert()`. Les envois échouent mais l’alerte reste dans SQLite. Toutes les dix mesures, `[COLLECTE]` affiche le compteur, l’état de la 4G et `pending_count()` : on voit que les mesures continuent pendant la panne.
3. À la **mesure 61, vers six secondes**, `sensor_samples()` rétablit automatiquement la 4G simulée. Le worker reprend l’envoi du même identifiant. Après le succès simulé, `delete_alert()` retire l’alerte ; la collecte continue jusqu’à la centième mesure.

**Bilan attendu : 100 mesures traitées, 1 freinage détecté et 0 alerte en attente.**

Les délais de reprise sont plafonnés à **2 secondes dans cette démonstration** pour garder une reprise rapide pendant la présentation. Aucune API externe n’est appelée : le succès de réception est simulé.

Chaque essai crée un sous-dossier distinct dans `resultats_demo`, avec sa base `events.sqlite` et son rapport `daily_score.json`. Les anciens résultats ne sont pas effacés. Le bloc `finally` demande l’arrêt du worker puis attend sa fin.

## 6. Tests automatisés

Tests Bloc 3 :

```bash
python -m pytest -q tests/bloc3
```

Suite complète du projet :

```bash
python -m pytest -q
```

Le résultat courant et le nombre exact de tests exécutés figurent dans [VALIDATION.txt](VALIDATION.txt).

## 7. Intégration et livraison continues

Le guide [CI_CD_DEMO.md](CI_CD_DEMO.md) détaille les sources et les étapes de présentation.

Le workflow `.github/workflows/bloc3-ci.yml` se déclenche sur un push, une Pull Request ou un lancement manuel. Il réalise :

1. les contrôles Ruff et mypy ;
2. les tests pytest, avec un rapport JUnit ;
3. les analyses Bandit, pip-audit et Gitleaks ;
4. la construction du ZIP et du manifeste, si les trois contrôles précédents réussissent ;
5. le staging simulé à partir du paquet construit.

`scripts/build_package.py` fabrique `dist/greenmove.zip` à partir des sources et des données. `dist/manifest.json` contient sa version, son commit et son SHA-256. L'artifact `greenmove-validated-package` devient disponible uniquement après le succès du staging.

Le second workflow, `.github/workflows/promote-demo.yml`, se lance manuellement avec l'identifiant `source_run_id` d'une CI réussie. Il récupère son paquet validé et simule sa promotion sans le reconstruire. Ce lancement représente le Go humain du POC.

## 8. Vérification du paquet construit

Depuis la racine du projet :

```bash
python -m scripts.build_package --version demo-local
python -m src.ota.check_manifest --manifest dist/manifest.json
```

Le SHA-256 est calculé sur le ZIP réellement produit. Si les octets du paquet ne correspondent plus au manifeste, la vérification échoue et la simulation OTA ne modifie pas l'état installé.

Ce contrôle d'intégrité n'est pas une signature cryptographique. L'ancien `src/ota/manifest.json`, son paquet de démonstration et sa `demo_signature` restent disponibles pour les tests historiques avec `python -m src.ota.check_manifest` sans argument. La nouvelle chaîne utilise le manifeste de `dist/`.

## 9. Staging, installation et rollback simulés

Pour montrer le scénario complet après le build :

```bash
python -m scripts.staging_demo --manifest dist/manifest.json --output-dir staging
```

Le script vérifie et extrait le paquet, puis exécute **le code extrait**. Il attend 100 mesures traitées, un freinage et aucune alerte restante après la reprise réseau. Il simule ensuite un échec d'installation : la version précédente est conservée. Enfin, il simule une installation réussie du même paquet.

Le rapport se trouve dans `staging/report.json` et le journal de collecte dans `staging/demo.log`. Sous Windows, `LANCER_LIVRAISON.bat` enchaîne le build et ce scénario.

Pour montrer séparément une installation puis un échec :

```bash
python -m src.ota.simulate_update --manifest dist/manifest.json --state-dir production-demo
python -m src.ota.simulate_update --manifest dist/manifest.json --state-dir production-demo --fail-install
```

La seconde commande retourne volontairement le code 1. `production-demo/ota_status.json` indique `rolled_back` et conserve la version précédemment installée. L'installation et le rollback modifient des fichiers JSON locaux : ils illustrent les concepts OTA, sans installer un système sur une tablette.

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
python -m pytest -q
python -m scripts.build_package --version demo-local
python -m scripts.staging_demo --manifest dist/manifest.json --output-dir staging
```

Le staging inclut déjà la démonstration de collecte et de reprise réseau. Sur GitHub, terminer par le lancement manuel de **Promotion manuelle - demonstration** avec l'identifiant de la CI réussie.

## 14. Limites du POC Bloc 3

Le dépôt démontre les principes d’industrialisation attendus pour l’épreuve.

Il ne prétend pas implémenter complètement :

- un backend OTA de production ;
- une PKI ou une signature asymétrique réelle ;
- un updater Android atomique ;
- une supervision de flotte complète ;
- un déploiement automatique vers 5 000 équipements.

Ces éléments constituent l’architecture cible décrite dans la vidéo.
