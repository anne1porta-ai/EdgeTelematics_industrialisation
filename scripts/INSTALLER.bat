@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto fin
".venv\Scripts\python.exe" -m pip install -r requirements.txt
:fin
pause
