# Démonstration CI/CD du Bloc 3

## But de la démonstration

Montrer qu'une version suit un chemin contrôlé avant sa promotion : elle est vérifiée, testée, construite, signée et exécutée en staging.

## Démonstration locale

```powershell
py lancer.py tests
py lancer.py build --version demo-local
py lancer.py staging
py lancer.py ota --mode rollout
```

## Preuves à montrer

| Preuve | Où la trouver | Résultat attendu |
|---|---|---|
| **Tests** | Terminal ou workflow CI | `55 passed` |
| **Paquet** | `dist/greenmove.zip` | ZIP créé une seule fois |
| **Manifeste** | `dist/manifest.json` | version, fichier et SHA-256 |
| **Staging** | `staging/report.json` | démonstration exécutée et checksum validé |
| **Rollback** | sortie du staging | version précédente conservée après l'échec simulé |
| **Promotion** | workflow `promote-demo.yml` | même artefact téléchargé, sans reconstruction |

## Enchaînement de la chaîne

```text
qualité et sécurité
        ↓
tests automatisés
        ↓
construction du paquet
        ↓
calcul du SHA-256
        ↓
signature et vérification
        ↓
staging
        ↓
décision humaine de promotion
        ↓
rollout progressif ou rollback
```

## Messages à expliquer à l'oral

- **Construire une seule fois** : le paquet promu est exactement celui qui a été testé.
- **SHA-256** : détecte une modification du fichier.
- **Signature** : vérifie que le paquet provient de la chaîne autorisée.
- **Staging** : vérifie le comportement du paquet avant la promotion.
- **Rollback** : protège la flotte si la nouvelle version devient instable.
- **Promotion manuelle** : représente la décision de Go après les contrôles automatiques.

## Périmètre

La chaîne prouve les mécanismes logiciels. Elle ne réalise pas une installation MDM sur de vraies tablettes. Cette étape devra être validée sur l'infrastructure cible.

[Guide de déploiement](README_DEPLOIEMENT.md) · [Détail de la chaîne](docs/CI_CD_ET_OTA.md)
