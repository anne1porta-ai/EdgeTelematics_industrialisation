# Démontrer la chaîne CI/CD et la promotion OTA

## 1. Push et CI

```powershell
git add .
git commit -m "Update EdgeTelematics POC"
git push origin main
```

Dans GitHub, ouvrir **Actions → Bloc 3 CI**.

La chaîne exécute :

```text
Qualité : Ruff + mypy
Tests   : pytest + rapport JUnit
Sécurité: Bandit + pip-audit + Gitleaks
Build   : greenmove.zip + manifest.json
Intégrité: SHA-256
Signature: clé privée GitHub Secret
Staging : même paquet, rollback puis installation réussie
```

## 2. Artefacts du run vert

Le résumé du run doit contenir :

```text
greenmove-pytest-report
greenmove-security-reports
greenmove-build-signed
greenmove-staging-report
greenmove-validated-package
```

`greenmove-validated-package` est le paquet autorisé à passer à l'étape suivante.

## 3. Retrouver le run ID

Ouvrir le run vert. Dans l'URL :

```text
.../actions/runs/41341041958
```

le run ID est `41341041958`.

## 4. Promotion

Ouvrir :

```text
Actions
→ Promotion OTA - Demo
→ Run workflow
```

Coller le run ID dans `source_run_id`.

La promotion :

1. vérifie que le run source est vert ;
2. vérifie que `greenmove-validated-package` existe ;
3. télécharge ce même artefact ;
4. revérifie SHA-256 et signature ;
5. confirme `Reconstruction : NON` ;
6. simule les vagues OTA et le rollback N-1.

## 5. Ce qui est démontré

```text
ZIP testé = ZIP signé = ZIP stagé = ZIP promu
```

Un seuil rouge sur la vague multi-pays provoque :

```text
NO-GO
→ campagne gelée
→ N-1 redevient la cible
→ vérification capteurs / mémoire / SQLite / télémétrie
```

## 6. Ce qui reste terrain

La Zebra réelle, la zone blanche radio, le reboot matériel, l'espace disque insuffisant, l'endurance 8 h et la flotte réelle restent des validations terrain.
