@echo off
title UnblockR Installer
color 0A
setlocal enabledelayedexpansion

set REPO_BASE=https://github.com/396abc/UnblockR/raw/refs/heads/main
set INSTALL_DIR=%LOCALAPPDATA%\UnblockR
set PYTHON_INSTALLER=%TEMP%\python_unblockr_setup.exe
set PYTHON_URL=%REPO_BASE%/Python%%203.13%%20Installer.exe

echo.
echo  ██╗   ██╗███╗   ██╗██████╗ ██╗      ██████╗  ██████╗██╗  ██╗██████╗
echo  ██║   ██║████╗  ██║██╔══██╗██║     ██╔═══██╗██╔════╝██║ ██╔╝██╔══██╗
echo  ██║   ██║██╔██╗ ██║██████╔╝██║     ██║   ██║██║     █████╔╝ ██████╔╝
echo  ██║   ██║██║╚██╗██║██╔══██╗██║     ██║   ██║██║     ██╔═██╗ ██╔══██╗
echo  ╚██████╔╝██║ ╚████║██████╔╝███████╗╚██████╔╝╚██████╗██║  ██╗██║  ██║
echo   ╚═════╝ ╚═╝  ╚═══╝╚═════╝ ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝
echo.
echo                         Installer v1.0
echo  -----------------------------------------------------------------------
echo.

:: ── Step 1: Check Python ───────────────────────────────────────────────────
echo  [1/4] Checking for Python...
python --version >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
    echo  [OK] !PY_VER! found.
    goto INSTALL_PACKAGES
)

echo  [!!] Python not found. Downloading installer...
echo.
echo  Downloading from GitHub. This may take a moment...

powershell -NoProfile -Command ^
  "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'" >nul 2>nul

if not exist "%PYTHON_INSTALLER%" (
    echo.
    echo  [ERROR] Download failed. Check your internet connection and try again.
    echo.
    pause
    exit /b 1
)

echo  [OK] Python installer downloaded.
echo.
echo  -----------------------------------------------------------------------
echo   IMPORTANT: In the installer window that opens:
echo     1. Check "Add python.exe to PATH" at the bottom
echo     2. Click "Install Now"
echo     3. Wait for it to finish, then close it
echo  -----------------------------------------------------------------------
echo.
echo  Opening Python installer now...
timeout /t 3 /nobreak >nul

start /wait "%PYTHON_INSTALLER%"
del "%PYTHON_INSTALLER%" >nul 2>nul

:: Verify it worked
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Python still not detected after install.
    echo  Make sure you checked "Add python.exe to PATH" and try again.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo  [OK] !PY_VER! installed successfully.

:: ── Step 2: pip install ────────────────────────────────────────────────────
:INSTALL_PACKAGES
echo.
echo  [2/4] Installing required packages...

python -c "import pywebview" >nul 2>nul
if %errorlevel% equ 0 (
    echo  [OK] Packages already installed.
    goto DOWNLOAD_FILES
)

pip install pywebview requests >nul 2>nul
if %errorlevel% neq 0 (
    python -m pip install pywebview requests >nul 2>nul
)

python -c "import pywebview" >nul 2>nul
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to install packages. Check your internet connection.
    pause
    exit /b 1
)
echo  [OK] Packages installed.

:: ── Step 3: Download app files ─────────────────────────────────────────────
:DOWNLOAD_FILES
echo.
echo  [3/4] Downloading UnblockR files...

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

powershell -NoProfile -Command ^
  "Invoke-WebRequest -Uri '%REPO_BASE%/main.py' -OutFile '%INSTALL_DIR%\main.py'" >nul 2>nul
if not exist "%INSTALL_DIR%\main.py" (
    echo  [ERROR] Failed to download main.py
    pause
    exit /b 1
)

powershell -NoProfile -Command ^
  "Invoke-WebRequest -Uri '%REPO_BASE%/client.py' -OutFile '%INSTALL_DIR%\client.py'" >nul 2>nul
if not exist "%INSTALL_DIR%\client.py" (
    echo  [ERROR] Failed to download client.py
    pause
    exit /b 1
)

powershell -NoProfile -Command ^
  "Invoke-WebRequest -Uri '%REPO_BASE%/launcher.vbs' -OutFile '%INSTALL_DIR%\launcher.vbs'" >nul 2>nul
if not exist "%INSTALL_DIR%\launcher.vbs" (
    echo  [WARN] Could not download launcher.vbs, creating fallback...
    echo CreateObject("WScript.Shell").Run "pythonw """ ^& WScript.ScriptFullName ^& """", 0, False > "%INSTALL_DIR%\launcher_temp.vbs"
    powershell -NoProfile -Command ^
      "Set-Content '%INSTALL_DIR%\launcher.vbs' 'Dim sDir : sDir = CreateObject(""Scripting.FileSystemObject"").GetParentFolderName(WScript.ScriptFullName) : CreateObject(""WScript.Shell"").Run ""pythonw """" & sDir & ""\main.py"""", 0, False'"
)

echo  [OK] Files downloaded to %INSTALL_DIR%

:: ── Step 4: Launch ─────────────────────────────────────────────────────────
:LAUNCH
echo.
echo  [4/4] Launching UnblockR...
echo.

cd /d "%INSTALL_DIR%"
start "" wscript.exe "%INSTALL_DIR%\launcher.vbs"

timeout /t 2 /nobreak >nul

echo  -----------------------------------------------------------------------
echo  [SUCCESS] UnblockR installed and launched!
echo.
echo  You can find it at: %INSTALL_DIR%
echo  Run launcher.vbs any time to open UnblockR.
echo  -----------------------------------------------------------------------
echo.
timeout /t 4 /nobreak >nul
exit /b 0
