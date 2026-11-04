# Clé de signature OTA de démonstration

Le projet fournit un script Python pour créer une paire de clés de démonstration.
Depuis la racine du dépôt :

**Windows :**

```powershell
py scripts/generate_demo_signing_keys.py
```

**Linux ou macOS :**

```bash
python3 scripts/generate_demo_signing_keys.py
```

Le script crée :

- `ota_private.pem` : clé privée de démonstration, à ne jamais envoyer dans Git ;
- `keys/ota_public.pem` : clé publique utilisée par la CI pour vérifier la signature.

Dans GitHub, créer ensuite le secret `OTA_SIGNING_PRIVATE_KEY` et y copier le
contenu complet de `ota_private.pem`.

Ces clés servent à la démonstration de la chaîne CI/CD. Elles ne constituent pas
une gestion de clés de production.
