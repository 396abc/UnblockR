@echo off
chcp 65001 >nul 2>nul
title UnblockR Installer
color 0A
setlocal enabledelayedexpansion

set REPO_BASE=https://github.com/396abc/UnblockR/raw/refs/heads/main
set INSTALL_DIR=%LOCALAPPDATA%\UnblockR
set PYTHON_INSTALLER=%TEMP%\python_unblockr_setup.exe
set PYTHON_URL=%REPO_BASE%/Python%203.13%20Installer.exe
set START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs

echo.
echo  ===================================================
echo               UnblockR  Installer  v1.0
echo  ===================================================
echo.

:: Step 1: Check Python
echo  [1/5] Checking for Python...
python --version >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
    echo  [OK] !PY_VER! found.
    goto INSTALL_PACKAGES
)

echo  [!!] Python not found. Downloading installer...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'" >nul 2>nul

if not exist "%PYTHON_INSTALLER%" (
    echo  [ERROR] Download failed. Check your internet connection.
    pause
    exit /b 1
)

echo  [OK] Python installer downloaded.
echo.
echo  ---------------------------------------------------
echo   IMPORTANT - In the installer window:
echo     1. Check "Add python.exe to PATH" at the bottom
echo     2. Click "Install Now"
echo     3. Wait for it to finish then close it
echo  ---------------------------------------------------
echo.
timeout /t 3 /nobreak >nul
start /wait "%PYTHON_INSTALLER%"
del "%PYTHON_INSTALLER%" >nul 2>nul

python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo  [ERROR] Python still not detected. Make sure you checked "Add to PATH".
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo  [OK] !PY_VER! installed.

:: Step 2: Install packages
:INSTALL_PACKAGES
echo.
echo  [2/5] Installing required packages...

python -c "import webview" >nul 2>nul
if %errorlevel% equ 0 (
    echo  [OK] Packages already installed.
    goto DOWNLOAD_FILES
)

pip install pywebview --upgrade
if %errorlevel% equ 0 goto PKGS_DONE
python -m pip install pywebview --upgrade
if %errorlevel% equ 0 goto PKGS_DONE

echo  [ERROR] Failed to install packages. Run manually: pip install pywebview
pause
exit /b 1

:PKGS_DONE
echo  [OK] Packages installed.

:: Step 3: Download files
:DOWNLOAD_FILES
echo.
echo  [3/5] Downloading UnblockR files...

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo  Downloading main.py...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%REPO_BASE%/main.py' -OutFile '%INSTALL_DIR%\main.py'" >nul 2>nul
if not exist "%INSTALL_DIR%\main.py" ( echo  [ERROR] Failed to download main.py & pause & exit /b 1 )

echo  Downloading updater.py...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%REPO_BASE%/updater.py' -OutFile '%INSTALL_DIR%\updater.py'" >nul 2>nul
if not exist "%INSTALL_DIR%\updater.py" ( echo  [WARN] updater.py download failed - updates will not work )

echo  Downloading launcher.vbs...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%REPO_BASE%/launcher.vbs' -OutFile '%INSTALL_DIR%\launcher.vbs'" >nul 2>nul
if not exist "%INSTALL_DIR%\launcher.vbs" (
    echo  [WARN] Download failed, writing fallback launcher.vbs...
    echo Dim sDir > "%INSTALL_DIR%\launcher.vbs"
    echo sDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) >> "%INSTALL_DIR%\launcher.vbs"
    echo CreateObject("WScript.Shell").Run "pythonw """ ^& sDir ^& "\main.py""", 0, False >> "%INSTALL_DIR%\launcher.vbs"
)

echo  Downloading updater_launcher.vbs...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%REPO_BASE%/updater_launcher.vbs' -OutFile '%INSTALL_DIR%\updater_launcher.vbs'" >nul 2>nul
if not exist "%INSTALL_DIR%\updater_launcher.vbs" (
    echo  [WARN] Download failed, writing fallback updater_launcher.vbs...
    echo Dim sDir > "%INSTALL_DIR%\updater_launcher.vbs"
    echo sDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) >> "%INSTALL_DIR%\updater_launcher.vbs"
    echo CreateObject("WScript.Shell").Run "pythonw """ ^& sDir ^& "\updater.py""", 0, False >> "%INSTALL_DIR%\updater_launcher.vbs"
)

echo  Downloading assets...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%REPO_BASE%/UnblockR.ico' -OutFile '%INSTALL_DIR%\UnblockR.ico'" >nul 2>nul
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/396abc/UnblockR/main/UnblockR.png' -OutFile '%INSTALL_DIR%\UnblockR.png'" >nul 2>nul

echo  [OK] All files saved to %INSTALL_DIR%

:: Step 4: Create shortcuts
echo.
echo  [4/5] Creating shortcuts...

powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%INSTALL_DIR%\UnblockR.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\""%INSTALL_DIR%\launcher.vbs\""'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.IconLocation = '%INSTALL_DIR%\UnblockR.ico'; $s.Description = 'UnblockR - Filtering Proxy Client'; $s.Save()" >nul 2>nul

if not exist "%START_MENU%\UnblockR" mkdir "%START_MENU%\UnblockR"
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%START_MENU%\UnblockR\UnblockR.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\""%INSTALL_DIR%\launcher.vbs\""'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.IconLocation = '%INSTALL_DIR%\UnblockR.ico'; $s.Description = 'UnblockR - Filtering Proxy Client'; $s.Save()" >nul 2>nul

echo  [OK] Shortcuts created.

:: Step 5: Launch
:LAUNCH
echo.
echo  [5/5] Launching UnblockR...

start "" wscript.exe "%INSTALL_DIR%\launcher.vbs"
timeout /t 2 /nobreak >nul

echo.
echo  ===================================================
echo   SUCCESS - UnblockR installed and launched!
echo   Location : %INSTALL_DIR%
echo   Start Menu: Search "UnblockR" in Start
echo  ===================================================
echo.
timeout /t 4 /nobreak >nul
exit /b 0
