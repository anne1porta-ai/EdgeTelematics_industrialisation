# Démontrer la chaîne CI/CD

Le projet fabrique un paquet, l'exécute en staging simulé, puis permet de promouvoir **ce même paquet** après un lancement manuel. La collecte Safety, SQLite et l'envoi dans leur thread existant servent de scénario de validation.

## 1. Les étapes et les sources

| Étape | Ce que la démo fait | Source |
|---|---|---|
| Qualité | Ruff contrôle le code ; mypy recherche les erreurs de types. | `.github/workflows/bloc3-ci.yml` |
| Tests | pytest exécute les tests et produit un rapport JUnit. | `.github/workflows/bloc3-ci.yml`, `tests/` |
| Sécurité | Bandit analyse Python, pip-audit audite les dépendances applicatives, Gitleaks recherche les secrets dans l'historique Git. | `.github/workflows/bloc3-ci.yml` |
| Build | Le ZIP contient les sources et les données du projet. Un manifeste associe version, commit et SHA-256. | `scripts/build_package.py` |
| Staging | Vérifier le SHA-256, extraire le ZIP, exécuter sa démo, simuler un échec avec rollback puis une installation réussie. | `scripts/staging_demo.py` |
| Go manuel | Choisir une exécution CI réussie et reprendre son paquet validé, sans le reconstruire. | `.github/workflows/promote-demo.yml` |
| Installation simulée | Vérifier le paquet puis écrire la version et le statut dans des fichiers JSON. | `src/ota/check_manifest.py`, `src/ota/simulate_update.py` |

La qualité, les tests et la sécurité doivent tous réussir avant le build. Le paquet n'est marqué comme validé qu'après la réussite du staging.

## 2. Montrer le résultat en local

Sous Windows, lancer `INSTALLER.bat` une fois, puis **`LANCER_LIVRAISON.bat`**. Ce second lanceur démontre le build et le staging ; les contrôles CI complets sont dans le workflow GitHub.

Dans un terminal avec les dépendances du projet installées, les mêmes étapes sont :

```bash
python -m scripts.build_package --version demo-local
python -m scripts.staging_demo --manifest dist/manifest.json --output-dir staging
```

Ce qui doit apparaître :

1. `dist/greenmove.zip` et `dist/manifest.json` sont créés.
2. Le code extrait du paquet traite **100 mesures**, détecte **1 freinage** et termine avec **0 alerte en attente**, après la coupure et la reprise réseau simulées.
3. L'échec d'installation volontaire conserve la version `2.2.0` : statut `rolled_back`.
4. L'installation suivante réussit : la version devient `demo-local` et le checksum reste celui du paquet construit.

Le bilan est dans `staging/report.json` ; le déroulé de la collecte dans `staging/demo.log`. Chaque essai conserve ses fichiers dans un sous-dossier `staging/essai-...`.

Le code de sortie 1 du simulateur pendant l'échec volontaire est attendu : `staging_demo.py` vérifie cet échec et poursuit le scénario. Un échec inattendu bloque le staging.

## 3. Utiliser les deux workflows sur GitHub

1. Placer les fichiers du projet, y compris `.github/workflows`, dans le dépôt GitHub.
2. Un push ou une Pull Request lance **Bloc 3 CI**. On peut aussi le lancer manuellement.
3. Ouvrir une exécution terminée avec succès. Ses artifacts contiennent les rapports et **`greenmove-validated-package`**.
4. Copier l'identifiant numérique situé à la fin de son URL : `.../actions/runs/123456789` donne `123456789`. Ce n'est pas le numéro d'affichage de l'exécution.
5. Dans **Actions → Promotion manuelle - demonstration → Run workflow**, saisir cet identifiant dans `source_run_id`, puis lancer.
6. Le second workflow vérifie l'origine et le succès du run, télécharge son paquet validé et simule sa promotion. Il conserve **`greenmove-promotion-status`** et **`greenmove-promoted-package`**.

Le bouton manuel nécessite que `promote-demo.yml` soit présent sur la branche par défaut et que l'utilisateur ait un accès en écriture au dépôt. Le lancement représente le **Go humain du POC** ; aucun rôle spécifique de CTO n'est imposé. Les artifacts sont conservés 30 jours.

Référence GitHub : [lancer un workflow manuellement](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

## 4. Ce qui est réel et ce qui est simulé

**Réel :** contrôles du code, tests, fabrication du ZIP, SHA-256, exécution des sources extraites, persistance SQLite et réutilisation du paquet entre les étapes.

**Simulé :** capteurs, coupure 4G, réception distante, installation sur une tablette et rollback. L'état OTA est un fichier JSON créé sur le runner ; chaque runner repart d'un état local neuf.

Cette démo ne réalise pas le test longue durée de huit heures sur une tablette Zebra, une signature cryptographique de production ou un déploiement progressif sur une flotte. Le SHA-256 contrôle l'intégrité du paquet par rapport au manifeste ; il ne constitue pas une signature. L'ancien exemple `src/ota/manifest.json` avec `demo_signature` reste disponible pour les tests historiques ; la nouvelle chaîne utilise **`dist/manifest.json`**.

Les validations locales effectuées sont consignées dans `VALIDATION.txt`. Les workflows sont fournis prêts à être exécutés dans le dépôt ; aucune exécution GitHub n'est déclarée comme réalisée lors de cette livraison.
