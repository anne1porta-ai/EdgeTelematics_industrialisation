@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" lancer.py tests
) else (
    python lancer.py tests
)
pause
