# Guide de démonstration

## 1. Démonstration standard

```powershell
py lancer.py demo
```

Cette commande exécute successivement :

- le moteur GEO sur `data/lyon_polygon.json` et `data/truck_gps.json` ;
- le moteur Safety sur `data/accelerometer_data.csv` ;
- la persistance des événements dans SQLite.

Résultats attendus :

- une entrée ZFE au point GPS `id=4`, à `08:00:30` ;
- un freinage à `acc_y=-3.45 m/s²`, à l'horodatage `1678880005` ;
- des événements conservés dans `greenmove.db` tant qu'aucune API n'est configurée.

## 2. Mode stress

```powershell
py lancer.py stress
```

Le script génère et traite 1 000 mesures représentant 10 secondes à 100 Hz. Il vérifie que la lecture reste progressive et qu'un seul freinage connu est détecté.

Ce mode augmente le volume de données, mais ne constitue pas un benchmark complet de la tablette.

## 3. Démonstration de résilience

```powershell
py lancer.py resilience
```

Déroulé conseillé à l'oral :

1. montrer le traitement en flux ;
2. lancer la coupure 4G simulée ;
3. montrer que la collecte continue ;
4. observer les retries et l'ouverture du circuit ;
5. rétablir le réseau et montrer `HALF_OPEN` puis `CLOSED` ;
6. montrer le timeout ;
7. envoyer deux fois le même identifiant et constater un seul stockage ;
8. afficher le bilan SQLite.

## 4. Tests

```powershell
py lancer.py tests
```

Résultat attendu :

```text
55 passed
```

## 5. Build et staging

```powershell
py lancer.py build --version demo-local
py lancer.py staging
```

Le build crée `dist/greenmove.zip` et `dist/manifest.json`. Le staging :

- vérifie le SHA-256 ;
- extrait et exécute le paquet ;
- contrôle le scénario de résilience ;
- simule un échec d'installation avec rollback ;
- installe ensuite le même paquet avec succès.

Le rapport est écrit dans `staging/report.json`.

## 6. Déploiement OTA simulé

```powershell
py lancer.py ota --mode staging
py lancer.py ota --mode rollout
```

Le rollout utilise plusieurs vagues et déclenche un `NO-GO` lorsque la stabilité passe sous le seuil de démonstration.

## 7. Gestion des erreurs

Les fonctions principales peuvent transmettre les erreurs au programme appelant. Le bilan Safety précédent est conservé si l'analyse échoue avant la fin. Les événements déjà persistés restent dans SQLite.

## 8. Points à expliquer au jury

- le calcul reste local et ne dépend pas de la 4G ;
- la collecte et le réseau sont séparés ;
- SQLite conserve les alertes avant l'envoi ;
- le backoff espace les tentatives, tandis que le circuit breaker protège le service distant ;
- l'idempotence évite un doublon lors d'un renvoi ;
- la chaîne OTA est une démonstration : elle ne déploie pas réellement sur une tablette Zebra.
