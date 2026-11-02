# Démonstration Déploiement OTA

Le push sur `main` déclenche :

```text
qualité -> tests -> sécurité -> build -> SHA-256 -> signature -> staging
```

Le run vert publie `greenmove-validated-package`.

Pour la promotion :

1. ouvrir le run `Bloc 3 CI` vert ;
2. copier l'identifiant après `/actions/runs/` ;
3. ouvrir `Actions -> Promotion OTA - Demo` ;
4. cliquer sur `Run workflow` ;
5. coller l'identifiant dans `source_run_id`.

Le workflow récupère le même artefact, vérifie le hash et la signature, puis simule les vagues OTA et le rollback N-1.
