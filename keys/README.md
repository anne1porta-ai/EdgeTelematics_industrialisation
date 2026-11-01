# OTA signing key

Run from PowerShell at the repository root:

```powershell
.\scripts\generate_demo_signing_keys.ps1
```

This creates:

- `ota_private.pem` — private demo signing key. **Never commit it.**
- `keys/ota_public.pem` — public verification key. Commit this file.

Then create a GitHub Actions secret named:

`OTA_SIGNING_PRIVATE_KEY`

and paste the complete contents of `ota_private.pem`.
