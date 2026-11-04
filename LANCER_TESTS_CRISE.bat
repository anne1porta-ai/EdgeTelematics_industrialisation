@echo off
chcp 65001 >nul
cd /d "%~dp0"
cls
echo ================================================================
echo     GREENMOVE - TESTS DE RESILIENCE ET CIRCUIT BREAKER
echo ================================================================
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m pytest -v tests\bloc3\test_crisis_regression.py tests\bloc3\test_circuit_breaker.py
) else (
    python -m pytest -v tests\bloc3\test_crisis_regression.py tests\bloc3\test_circuit_breaker.py
)
echo.
echo Ces tests couvrent : traitement en flux, decouplage reseau,
echo SQLite, retry/backoff, circuit breaker, archivage,
echo HTTPS, idempotence et timeout.
echo.
pause
