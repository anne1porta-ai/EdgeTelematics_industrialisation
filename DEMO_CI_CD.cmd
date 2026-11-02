@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title GreenMove - Demo CI/CD

set "PY=.venv\Scripts\python.exe"
set "VERSION=1.2-DEMO"

cls
echo ================================================================
echo              DEMO CI/CD - EDGE TELEMATICS
echo ================================================================
echo.
echo  Pipeline local de demonstration :
echo  QUALITE ^> TESTS ^> SECURITE ^> BUILD ^> HASH ^> STAGING
echo.
echo  Une etape en echec arrete immediatement la chaine.
echo ================================================================
echo.

if not exist "%PY%" (
    echo [ERREUR] Environnement Python .venv introuvable.
    echo Lance d'abord INSTALLER.bat
    echo.
    pause
    exit /b 1
)

REM -----------------------------------------------------------------
echo [1/6] QUALITE - Ruff
echo -----------------------------------------------------------------
"%PY%" -m ruff check src scripts tests run_demo.py run_bloc3_demo.py
if errorlevel 1 goto :failed
echo [OK] Ruff
echo.

echo [1/6] QUALITE - mypy
"%PY%" -m mypy --explicit-package-bases --check-untyped-defs src scripts run_demo.py run_bloc3_demo.py
if errorlevel 1 goto :failed
echo [OK] mypy
echo.
pause

REM -----------------------------------------------------------------
echo.
echo [2/6] TESTS AUTOMATISES - pytest
echo -----------------------------------------------------------------
"%PY%" -m pytest -q --junitxml=report.xml
if errorlevel 1 goto :failed
echo [OK] Tests automatises
echo [PREUVE] report.xml genere
echo.
pause

REM -----------------------------------------------------------------
echo.
echo [3/6] SECURITE
echo -----------------------------------------------------------------
echo Bandit...
"%PY%" -m bandit -r src scripts -x tests,scripts/tests
if errorlevel 1 goto :failed
echo [OK] Bandit
echo.

echo pip-audit...
"%PY%" -m pip_audit -r requirements.txt
if errorlevel 1 goto :failed
echo [OK] pip-audit
echo.

where gitleaks >nul 2>&1
if errorlevel 1 (
    echo [INFO] Gitleaks non installe localement.
    echo [INFO] Le controle Gitleaks est execute dans GitHub Actions.
) else (
    echo Gitleaks...
    gitleaks detect --source . --no-banner
    if errorlevel 1 goto :failed
    echo [OK] Gitleaks
)
echo.
pause

REM -----------------------------------------------------------------
echo.
echo [4/6] BUILD - ARTEFACT OTA
echo -----------------------------------------------------------------
for /f %%i in ('git rev-parse --short HEAD 2^>nul') do set "COMMIT=%%i"
if not defined COMMIT set "COMMIT=local"

if exist scripts\build_ota_package.py (
    "%PY%" scripts\build_ota_package.py --version "%VERSION%" --commit "%COMMIT%"
    if errorlevel 1 goto :failed
) else if exist scripts\build_package.py (
    "%PY%" scripts\build_package.py --version "%VERSION%" --commit "%COMMIT%"
    if errorlevel 1 goto :failed
) else (
    echo [ERREUR] Aucun script de build OTA trouve.
    goto :failed
)

echo [OK] Artefact construit
echo.
pause

REM -----------------------------------------------------------------
echo.
echo [5/6] INTEGRITE - SHA-256
echo -----------------------------------------------------------------
set "PACKAGE="
for %%F in (dist\edge-telematics-%VERSION%.zip) do (
    if exist "%%F" set "PACKAGE=%%F"
)

if not defined PACKAGE (
    for /f "delims=" %%F in ('dir /b /o-d dist\*.zip 2^>nul') do (
        if not defined PACKAGE set "PACKAGE=dist\%%F"
    )
)

if not defined PACKAGE (
    echo [ERREUR] Aucun ZIP trouve dans dist\
    goto :failed
)

echo Artefact : %PACKAGE%
certutil -hashfile "%PACKAGE%" SHA256
if errorlevel 1 goto :failed
echo [OK] SHA-256 calcule
echo.
echo [INFO] La signature cryptographique et sa verification sont
echo        realisees par GitHub Actions avec OTA_SIGNING_PRIVATE_KEY.
echo.
pause

REM -----------------------------------------------------------------
echo.
echo [6/6] STAGING / DEPLOIEMENT CONTROLE
echo -----------------------------------------------------------------
if exist scripts\staging_demo.py (
    "%PY%" scripts\staging_demo.py
    if errorlevel 1 goto :failed
    echo [OK] Staging
) else (
    echo [INFO] scripts\staging_demo.py absent - etape non executee.
)

if exist scripts\demo_ota_rollout.py (
    echo.
    echo Simulation des vagues OTA et du rollback N-1...
    "%PY%" scripts\demo_ota_rollout.py --mode rollout
    if errorlevel 1 goto :failed
)

echo.
echo ================================================================
echo                    PIPELINE TERMINE
echo ================================================================
echo [OK] Qualite
echo [OK] Tests
echo [OK] Securite
echo [OK] Artefact construit
echo [OK] SHA-256
echo [OK] Staging / deploiement simule
echo.
echo La signature OTA complete se montre dans GitHub Actions :
echo Build OTA - hash and signature ^> greenmove-validated-package
echo ================================================================
echo.
pause
exit /b 0

:failed
echo.
echo ================================================================
echo                    PIPELINE BLOQUE
echo ================================================================
echo [STOP] Une barriere a echoue.
echo Aucun passage a l'etape suivante.
echo ================================================================
echo.
pause
exit /b 1
