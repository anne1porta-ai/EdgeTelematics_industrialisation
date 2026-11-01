# Modifications de la version simplifiée

## Objectif

Conserver les fonctionnalités, les tests et les démonstrations tout en rendant le code plus direct et plus facile à expliquer.

## Simplifications réalisées

- suppression de la copie complète du projet qui se trouvait dans `scripts/` ;
- suppression du second script de build OTA inutilisé ;
- suppression du script PowerShell de clés dépendant d'OpenSSL local ;
- conservation d'un seul générateur de clés en Python ;
- suppression de l'ancien fichier de dépendances notebook ;
- `run_demo.py` n'implémente plus deux fois la gestion du buffer ;
- noms plus explicites dans la démonstration ;
- staging non interactif grâce à `stdin=DEVNULL` ;
- contrôle de l'historique `synced=1` pendant le staging.

## Fonctionnalités conservées

- Geo et Safety ;
- mémoire bornée ;
- mode stress ;
- `TelemetryEvent` ;
- SQLite et Store-and-Forward ;
- backoff ;
- timeout ;
- idempotence ;
- historique synchronisé ;
- 49 tests ;
- démo de crise ;
- paquet `.pkg` historique ;
- build ZIP, signature, staging, promotion et rollback OTA.

## Fichiers principaux modifiés

```text
run_demo.py
run_bloc3_demo.py
src/safety/run_safety.py
scripts/generate_demo_signing_keys.py
scripts/demo_ota_rollout.py
scripts/staging_demo.py
COMMENCER_ICI.txt
README.md
README_BLOC3.md
CI_CD_DEMO.md
VALIDATION.txt
```
