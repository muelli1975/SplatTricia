@echo off
setlocal EnableExtensions
cd /d "%~dp0"

for %%P in (build dist build_native source) do (
    if exist "%%P" rmdir /s /q "%%P"
)

if exist "LICENSES.txt" del /q "LICENSES.txt"
if exist "requirements-lock.txt" del /q "requirements-lock.txt"
if exist "splattricia_error.log" del /q "splattricia_error.log"

for /d /r %%D in (__pycache__) do @if exist "%%D" rd /s /q "%%D"
for /r %%F in (*.pyc *.pyo) do @if exist "%%F" del /q "%%F"

echo Projekt-Artefakte entfernt.
endlocal
