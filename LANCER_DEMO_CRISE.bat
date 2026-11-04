@echo off
chcp 65001 >nul
cd /d "%~dp0"
cls
echo ================================================================
echo          GREENMOVE - DEMO RESILIENCE APRES INCIDENT
echo ================================================================
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -u lancer.py resilience
) else (
    python -u lancer.py resilience
)
echo.
echo ================================================================
echo Fin de la demonstration. La fenetre reste ouverte pour l'oral.
echo ================================================================
pause
