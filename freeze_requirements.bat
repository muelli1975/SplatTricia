@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo FEHLER: venv\Scripts\python.exe fehlt.
    exit /b 1
)
"venv\Scripts\python.exe" -m pip list --format=freeze > requirements-lock.txt
if errorlevel 1 exit /b 1
echo requirements-lock.txt wurde erstellt.
endlocal
