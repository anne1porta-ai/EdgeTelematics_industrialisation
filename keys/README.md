# Clé de signature OTA

Le dépôt contient déjà la clé publique utilisée par GitHub Actions :

```text
keys/ota_public.pem
```

La clé privée correspondante doit rester uniquement dans le secret GitHub :

```text
OTA_SIGNING_PRIVATE_KEY
```

## Remplacer volontairement la paire de clés

Ne régénérer les clés que si le secret GitHub doit aussi être remplacé.

```powershell
.\.venv\Scripts\python.exe -m pip install cryptography
Remove-Item .\keys\ota_public.pem
.\.venv\Scripts\python.exe .\scripts\generate_demo_signing_keys.py
```

Le script crée :

- `ota_private.pem` : clé privée, interdite dans Git ;
- `keys/ota_public.pem` : clé publique à committer.

Copier ensuite tout le contenu de `ota_private.pem` dans le secret GitHub `OTA_SIGNING_PRIVATE_KEY`, puis supprimer le fichier local si souhaité.

Le script refuse d'écraser une paire existante afin d'éviter de désynchroniser la clé publique et le secret GitHub.
