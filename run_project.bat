@echo off
setlocal
cd /d "%~dp0"
echo ETF Portfolio Construction - research environment
echo Please leave this window open while the notebook runs.
echo.

rem Prefer a supported Python; do not install into the system environment.
for %%V in (3.13 3.12 3.11) do (
    py -%%V -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] <= (3,13) else 1)" >nul 2>&1
    if not errorlevel 1 (
        py -%%V launch.py %*
        goto finished
    )
)
python -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] <= (3,13) else 1)" >nul 2>&1
if not errorlevel 1 (
    python launch.py %*
    goto finished
)
echo Python 3.11, 3.12 or 3.13 was not found.
echo Install 64-bit Python from https://www.python.org/downloads/ .
echo Enable Add python.exe to PATH if the installer offers it.
echo Then close this window and double-click run_project.bat again.
pause
exit /b 2

:finished
set "portfolio_exit=%errorlevel%"
if not "%portfolio_exit%"=="0" (
    echo.
    echo Setup could not finish. Read the message above and README.md Troubleshooting.
)
pause
exit /b %portfolio_exit%
