# Déploiement — CI/CD, OTA et rollback

## Objectif

Construire une version une seule fois, vérifier son intégrité, la tester en staging, puis promouvoir **le même paquet** sans le reconstruire.

Cette règle évite qu'une version différente de celle testée arrive en déploiement.

## Chaîne automatisée

```text
Ruff → mypy → pytest → Bandit → pip-audit → Gitleaks
     → build → SHA-256 → signature → staging → promotion
```

| Étape | Ce qu'elle apporte |
|---|---|
| **Qualité** | Détecter des erreurs de style ou de typage. |
| **Tests** | Vérifier les comportements attendus avec pytest. |
| **Sécurité** | Contrôler le code, les dépendances et les secrets. |
| **Build** | Créer `greenmove.zip` et son manifeste. |
| **SHA-256** | Vérifier que le paquet n'a pas été modifié. |
| **Signature** | Vérifier l'origine du paquet validé par la CI. |
| **Staging** | Exécuter le paquet avant sa promotion. |
| **Promotion** | Réutiliser le même artefact validé. |
| **Rollback** | Revenir à la version N-1 si la stabilité devient insuffisante. |

## Démonstration locale

```powershell
py lancer.py build --version demo-local
py lancer.py staging
py lancer.py ota --mode rollout
```

Le raccourci Windows reste disponible :

```powershell
.\LANCER_LIVRAISON.bat
```

### Résultats attendus

1. `dist/greenmove.zip` et `dist/manifest.json` sont créés.
2. Le SHA-256 du paquet est vérifié.
3. Le paquet extrait exécute la démonstration de résilience.
4. Un échec volontaire conserve la version précédente.
5. Une nouvelle tentative installe le même paquet avec succès.
6. Le rollout s'arrête et revient à N-1 si le seuil de stabilité n'est plus respecté.

## Promotion manuelle dans GitHub Actions

1. Ouvrir un run vert du workflow **Bloc 3 CI**.
2. Copier l'identifiant du run dans son URL `/actions/runs/...`.
3. Ouvrir **Actions → Promotion OTA - Demo**.
4. Cliquer sur **Run workflow**.
5. Saisir l'identifiant dans `source_run_id`.

Le workflow récupère l'artefact déjà validé, contrôle son origine, son hash et sa signature, puis lance la simulation de promotion.

## Clés de signature

```powershell
py scripts/generate_demo_signing_keys.py
```

Le script crée :

- `ota_private.pem`, à conserver hors de Git ;
- `keys/ota_public.pem`, utilisée pour vérifier la signature.

La clé privée doit être enregistrée dans le secret GitHub `OTA_SIGNING_PRIVATE_KEY`.

## Ce qui est réel et ce qui est simulé

**Réel :** tests, build, SHA-256, signature CI, vérification, exécution du paquet extrait et promotion du même artefact.

**Simulé :** MDM, installation physique sur Zebra, vagues d'une flotte réelle et rollback Android de production.

[Retour au Bloc 3](README_BLOC3.md) · [Détail CI/CD](docs/CI_CD_ET_OTA.md)
