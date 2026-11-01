@echo off
chcp 65001 >nul
cls
echo ================================================================
echo          GREENMOVE - DEMO RESILIENCE APRES INCIDENT
echo ================================================================
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -u run_bloc3_demo.py
) else (
    python -u run_bloc3_demo.py
)
echo.
echo ================================================================
echo Fin de la demonstration. La fenetre reste ouverte pour l'oral.
echo ================================================================
pause
