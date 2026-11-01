@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m scripts.build_package --version demo-local
if errorlevel 1 goto fin
".venv\Scripts\python.exe" -m scripts.staging_demo
:fin
pause
