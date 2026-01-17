@echo off
setlocal EnableDelayedExpansion
TITLE Audiobook Studio Launcher

:: ====================================================
:: 0. CONFIGURATION
:: ====================================================
:: I set this to match the name in your logs
set DOCKER_IMAGE_NAME=arkoto123/epub-to-mp3:latest

:: ====================================================
:: 1. CHECK FOR ADMIN PRIVILEGES
:: ====================================================
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
cls

echo ========================================================
echo      AUDIOBOOK STUDIO - AUTO INSTALLER AND LAUNCHER
echo ========================================================
echo.

:: ====================================================
:: 2. CHECK & INSTALL DOCKER
:: ====================================================
echo [1/5] Checking System Dependencies...

where docker >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARN] Docker is NOT installed.
    echo --------------------------------------------------------
    echo    Installing Docker Desktop automatically...
    echo    This will take a few minutes. Please wait.
    echo --------------------------------------------------------
    echo.
    
    winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
    
    if %errorLevel% neq 0 (
        echo.
        echo [ERROR] Automatic installation failed.
        echo Please download Docker Desktop manually: https://www.docker.com/products/docker-desktop/
        pause
        exit
    )
    
    echo.
    echo [SUCCESS] Docker installed! 
    echo [IMPORTANT] Please RESTART your computer now.
    echo [INFO] After restarting, run this script again.
    pause
    exit
) else (
    echo [OK] Docker is installed.
)

:: ====================================================
:: 3. WAKE UP DOCKER ENGINE
:: ====================================================
echo [2/5] Checking Docker Engine status...

docker ps >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Docker Engine is not running. Starting it now...
    
    if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
        start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    ) else (
        echo [WARN] Could not find shortcut. Please open Docker Desktop manually.
    )
    
    echo [WAIT] Waiting for Docker to initialize...
    
    :WAIT_LOOP
    timeout /t 5 /nobreak >nul
    docker ps >nul 2>&1
    if %errorLevel% neq 0 (
        echo ... starting engine ...
        goto WAIT_LOOP
    )
    echo [OK] Docker Engine is active!
)

:: ====================================================
:: 4. UPDATE APP FROM CLOUD
:: ====================================================
echo [3/5] Downloading latest version...
echo        Target: %DOCKER_IMAGE_NAME%

docker pull %DOCKER_IMAGE_NAME%

:: ====================================================
:: 5. LAUNCH CONTAINER
:: ====================================================
echo [4/5] Starting Audiobook Studio...

:: Clean up old instances
docker rm -f epub-studio-instance >nul 2>&1

:: Run the app
docker run -d ^
  -p 8501:8501 ^
  --name epub-studio-instance ^
  --restart unless-stopped ^
  %DOCKER_IMAGE_NAME%

:: ====================================================
:: 6. OPEN BROWSER
:: ====================================================
echo.
echo [5/5] Launching Interface...
timeout /t 3 /nobreak >nul

echo.
echo ========================================================
echo        SUCCESS! APP IS RUNNING
echo ========================================================
echo.
echo  - Web Interface: http://localhost:8501
echo.
echo  You can close this window. The app runs in the background.
echo.

start http://localhost:8501

pause