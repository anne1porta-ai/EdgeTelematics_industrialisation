@echo off
chcp 65001 >nul
cls
echo ================================================================
echo        GREENMOVE - 6 TESTS DE NON-REGRESSION DE CRISE
echo ================================================================
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m pytest -v tests\bloc3\test_crisis_regression.py
) else (
    python -m pytest -v tests\bloc3\test_crisis_regression.py
)
echo.
echo Ces tests couvrent : traitement en flux, decouplage reseau,
echo SQLite, retry/backoff, archivage, HTTPS-idempotence-timeout.
echo.
pause
