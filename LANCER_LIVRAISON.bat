@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)
%PY% lancer.py build --version demo-local
if errorlevel 1 goto fin
%PY% lancer.py staging
:fin
pause
