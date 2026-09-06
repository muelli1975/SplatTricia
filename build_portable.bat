@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "APP_NAME=SplatTricia"
set "VERSION=1.0"
set "PYTHON=%CD%\venv\Scripts\python.exe"
set "PYINSTALLER=%CD%\venv\Scripts\pyinstaller.exe"
set "DIST_DIR=%CD%\dist\%APP_NAME%"
set "ZIP_PATH=%CD%\dist\%APP_NAME%_%VERSION%.zip"

if not exist "%PYTHON%" (
    echo FEHLER: venv\Scripts\python.exe fehlt.
    exit /b 1
)
if not exist "%PYINSTALLER%" (
    echo FEHLER: PyInstaller fehlt im venv.
    exit /b 1
)
if not exist "models\sharp_2572gikvuh.pt" (
    echo FEHLER: SHARP-Checkpoint fehlt unter models\sharp_2572gikvuh.pt.
    exit /b 1
)
if not exist "assets\splattricia.ico" (
    echo FEHLER: assets\splattricia.ico fehlt.
    exit /b 1
)
if not exist "assets\ready.wav" (
    echo FEHLER: assets\ready.wav fehlt.
    exit /b 1
)
if not exist "tools\exiftool.exe" (
    echo FEHLER: tools\exiftool.exe fehlt.
    exit /b 1
)
if not exist "LICENSE.txt" (
    echo FEHLER: LICENSE.txt fehlt.
    exit /b 1
)

for %%P in (build dist build_native) do (
    if exist "%%P" rmdir /s /q "%%P"
)
if exist "source" rmdir /s /q "source"
if exist "LICENSES.txt" del /q "LICENSES.txt"
if exist "requirements-lock.txt" del /q "requirements-lock.txt"

set "CUDA_FOUND="
for %%P in (
    "%ProgramFiles%\NVIDIA GPU Computing Toolkit\CUDA\v13.0\bin\nvcc.exe"
    "%ProgramFiles%\NVIDIA GPU Computing Toolkit\CUDA\v12.9\bin\nvcc.exe"
    "%ProgramFiles%\NVIDIA GPU Computing Toolkit\CUDA\v12.8\bin\nvcc.exe"
    "%ProgramFiles%\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin\nvcc.exe"
    "%ProgramFiles%\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin\nvcc.exe"
    "%ProgramFiles%\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin\nvcc.exe"
) do (
    if not defined CUDA_FOUND if exist "%%~P" set "CUDA_FOUND=%%~P"
)
if not defined CUDA_FOUND (
    echo FEHLER: Kein nvcc.exe in den erwarteten CUDA-Pfaden gefunden.
    exit /b 1
)
for %%I in ("!CUDA_FOUND!") do for %%J in ("%%~dpI..") do set "CUDA_HOME=%%~fJ"
set "PATH=!CUDA_HOME!\bin;!PATH!"

echo [1/7] Python-Umgebung dokumentieren ...
"!PYTHON!" -m pip list --format=freeze > requirements-lock.txt
if errorlevel 1 (
    echo FEHLER: requirements-lock.txt konnte nicht erstellt werden.
    exit /b 1
)

echo [2/7] gsplat Multi-Arch-Erweiterung bauen ...
set "TORCH_CUDA_ARCH_LIST=7.5;8.0;8.6;8.9;9.0+PTX"
"!PYTHON!" prepare_gsplat_native.py
if errorlevel 1 exit /b 1

echo [3/7] Source-Snapshot vorbereiten ...
"!PYTHON!" prepare_source_bundle.py
if errorlevel 1 exit /b 1

echo [4/7] PyInstaller ...
"!PYINSTALLER!" --noconfirm --clean SplatTricia.spec
if errorlevel 1 exit /b 1

echo [5/7] Lizenzen sammeln ...
"!PYTHON!" collect_licenses.py --output "!DIST_DIR!\LICENSES.txt"
if errorlevel 1 exit /b 1
copy /y LICENSE.txt "!DIST_DIR!\LICENSE.txt" >nul
copy /y README_DE.txt "!DIST_DIR!\README_DE.txt" >nul
copy /y README_EN.txt "!DIST_DIR!\README_EN.txt" >nul

if not exist "!DIST_DIR!\source\LICENSE.txt" (
    echo FEHLER: source\LICENSE.txt fehlt im Release.
    exit /b 1
)

if not exist "!DIST_DIR!\source\requirements-lock.txt" (
    echo FEHLER: requirements-lock.txt fehlt im Source-Snapshot.
    exit /b 1
)

if exist "!DIST_DIR!\models\sharp_2572gikvuh.pt" (
    del /q "!DIST_DIR!\models\sharp_2572gikvuh.pt"
)

echo [6/7] Release pruefen ...
"!PYTHON!" verify_release.py --dist "!DIST_DIR!"
if errorlevel 1 exit /b 1

echo [7/7] ZIP erstellen ...
if exist "!ZIP_PATH!" del /q "!ZIP_PATH!"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Compress-Archive -Path '!DIST_DIR!\*' -DestinationPath '!ZIP_PATH!' -CompressionLevel Optimal"
if errorlevel 1 exit /b 1

echo.
echo Fertig: !ZIP_PATH!
endlocal
