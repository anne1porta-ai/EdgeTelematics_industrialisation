$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path keys | Out-Null

Write-Host "Generation d'une paire RSA de DEMONSTRATION..."
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out ota_private.pem
openssl rsa -pubout -in ota_private.pem -out keys\ota_public.pem

Write-Host ""
Write-Host "CREE : ota_private.pem"
Write-Host "CREE : keys\ota_public.pem"
Write-Host ""
Write-Host "IMPORTANT :"
Write-Host "- Ne committez JAMAIS ota_private.pem."
Write-Host "- Copiez son contenu dans GitHub > Settings > Secrets and variables > Actions"
Write-Host "- Nom du secret : OTA_SIGNING_PRIVATE_KEY"
Write-Host "- La cle publique keys\ota_public.pem peut etre committee."
