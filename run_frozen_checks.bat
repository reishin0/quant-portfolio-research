@echo off
setlocal
cd /d "%~dp0"
echo Quant Portfolio Research - frozen protocol verification
echo Installs the exact protocol package versions, then verifies every frozen record.
echo Please leave this window open until it finishes.
echo.

rem The frozen protocols pin exact numpy/pandas/scipy/calendar versions.
rem Wheels for those versions exist for 64-bit Python 3.13 and 3.12 on Windows.
set "PIP_CONSTRAINT=%~dp0constraints-frozen.txt"
set "PY="
for %%V in (3.13 3.12) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1
        if not errorlevel 1 set "PY=py -%%V"
    )
)
if not defined PY (
    echo 64-bit Python 3.13 or 3.12 was not found.
    echo Install it from https://www.python.org/downloads/ and run this file again.
    pause
    exit /b 2
)

echo [1/4] Preparing .venv with the frozen package versions...
%PY% launch.py --repair --check
if errorlevel 1 goto failed

echo.
echo [2/4] Verifying the frozen forward protocol...
".venv\Scripts\python.exe" forward_evaluation.py
if errorlevel 1 goto failed

echo.
echo [3/4] Verifying the reviewed publication snapshot...
".venv\Scripts\python.exe" review_checks.py
if errorlevel 1 goto failed

echo.
echo [4/4] Re-executing the reviewed amendment notebook...
".venv\Scripts\python.exe" run_reviewed_analysis.py
if errorlevel 1 goto failed

echo.
echo SUCCESS: all frozen checks passed. Reports are in the outputs folder.
pause
exit /b 0

:failed
set "frozen_exit=%errorlevel%"
echo.
echo A frozen check stopped. Read the message above and README.md ^> Troubleshooting.
pause
exit /b %frozen_exit%
