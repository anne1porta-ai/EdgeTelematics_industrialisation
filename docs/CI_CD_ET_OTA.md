# CI/CD et OTA

## Chaîne GitHub Actions

Le workflow `.github/workflows/bloc3-ci.yml` suit cet ordre :

```text
Ruff → mypy → pytest → Bandit → pip-audit → Gitleaks
     → build → SHA-256 → signature → staging
```

| Étape | Preuve produite |
|---|---|
| Qualité | Vérification Ruff et mypy. |
| Tests | Rapport JUnit pytest. |
| Sécurité | Rapports Bandit, pip-audit et Gitleaks. |
| Build | ZIP, manifeste et SHA-256. |
| Signature | Signature du ZIP avec la clé privée stockée dans GitHub Secrets. |
| Staging | Exécution du paquet, rollback simulé puis installation réussie. |
| Promotion | Réutilisation du même paquet validé, sans reconstruction. |

## Démonstration locale

```powershell
py lancer.py build --version demo-local
py lancer.py staging
```

Le staging attend :

```text
160 mesures
1 freinage
0 alerte en attente
1 alerte synchronisée
rollback observé
installation réussie avec le même checksum
```

## Promotion GitHub

1. Lancer ou attendre un run vert du workflow **Bloc 3 CI**.
2. Copier l'identifiant numérique du run GitHub Actions.
3. Ouvrir **Promotion OTA - Demo**.
4. Lancer manuellement le workflow avec `source_run_id`.
5. Le workflow vérifie le run source et télécharge `greenmove-validated-package`.
6. Le SHA-256 et la signature sont revérifiés avant le rollout simulé.

Le lancement manuel représente le Go humain de la démonstration.

## Clés de signature

Depuis la racine :

```powershell
py scripts/generate_demo_signing_keys.py
```

Le script crée :

- `ota_private.pem`, à conserver hors de Git ;
- `keys/ota_public.pem`, utilisée pour la vérification.

Le contenu de la clé privée doit être enregistré dans le secret GitHub `OTA_SIGNING_PRIVATE_KEY`.

## Deux mécanismes OTA distincts

Le projet conserve un ancien exemple dans `src/ota/manifest.json`. Sa `demo_signature` est déterministe et pédagogique.

La chaîne CI principale utilise une méthode différente :

- ZIP construit une seule fois ;
- SHA-256 ;
- signature asymétrique avec OpenSSL ;
- vérification avec `keys/ota_public.pem` ;
- promotion du même artefact.

L'ancien exemple ne doit pas être présenté comme une signature de production.

## Ce qui est réel et ce qui est simulé

**Réel :** contrôles de qualité, tests, build, hash, signature CI, vérification, exécution du ZIP extrait et réutilisation du même paquet.

**Simulé :** capteurs, API distante, installation Android, MDM, vagues de flotte et rollback sur une Zebra réelle.
