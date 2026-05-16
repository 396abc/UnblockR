@echo off
chcp 65001 >nul 2>nul
title UnblockR Installer
setlocal enabledelayedexpansion

set REPO_BASE=https://github.com/396abc/UnblockR/raw/refs/heads/main
set INSTALL_DIR=%LOCALAPPDATA%\UnblockR
set PYTHON_INSTALLER=%TEMP%\python_unblockr_setup.exe
set PYTHON_URL=https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe
set START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs

cls
echo  ================================================
echo              UnblockR Installer v1.1
echo  ================================================
echo.

:: Step 1: Check Python
echo  [1/5] Checking for Python...
python --version >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
    echo        !PY_VER! detected.
    goto INSTALL_PACKAGES
)

echo        Not found. Downloading from python.org...
curl -L -o "%PYTHON_INSTALLER%" "%PYTHON_URL%" ^
    -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36" ^
    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" ^
    -H "Accept-Language: en-US,en;q=0.5" ^
    --retry 3 --retry-delay 5 -# 2>nul

if not exist "%PYTHON_INSTALLER%" (
    echo        [FAIL] Could not download Python installer.
    echo        Check your internet connection.
    pause
    exit /b 1
)

echo        Installing Python silently...
start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 2>nul
del "%PYTHON_INSTALLER%" >nul 2>nul

:: Refresh PATH
set "PATH=%PATH%;C:\Program Files\Python313\Scripts;C:\Program Files\Python313;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\Scripts;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313"

python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo        [FAIL] Python not detected after install.
    echo        Reboot your PC and try again.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo        !PY_VER! installed.

:: Step 2: Install packages
:INSTALL_PACKAGES
echo.
echo  [2/5] Checking packages...

set PKG_FAIL=0

echo        webview...
python -c "import webview" 2>nul
if %errorlevel% neq 0 (
    pip install pywebview --upgrade -q 2>nul
    if %errorlevel% neq 0 (
        python -m pip install pywebview --upgrade -q 2>nul
        if %errorlevel% neq 0 set PKG_FAIL=1
    )
)

echo        psutil...
python -c "import psutil" 2>nul
if %errorlevel% neq 0 (
    pip install psutil --upgrade -q 2>nul
    if %errorlevel% neq 0 (
        python -m pip install psutil --upgrade -q 2>nul
        if %errorlevel% neq 0 set PKG_FAIL=1
    )
)

echo        websocket-client...
python -c "import websocket" 2>nul
if %errorlevel% neq 0 (
    pip install websocket-client --upgrade -q 2>nul
    if %errorlevel% neq 0 (
        python -m pip install websocket-client --upgrade -q 2>nul
        if %errorlevel% neq 0 set PKG_FAIL=1
    )
)

if %PKG_FAIL% equ 1 (
    echo        [WARN] Some packages failed. The app may not work.
    echo        Run: pip install pywebview psutil websocket-client
)

echo        Done.

:: Step 3: Download files
:DOWNLOAD_FILES
echo.
echo  [3/5] Downloading UnblockR files...

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%" >nul 2>nul

set DL_FAIL=0

powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%REPO_BASE%/main.py', '%INSTALL_DIR%\main.py')" >nul 2>nul
if not exist "%INSTALL_DIR%\main.py" ( echo        [FAIL] main.py & set DL_FAIL=1 )

powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%REPO_BASE%/updater.py', '%INSTALL_DIR%\updater.py')" >nul 2>nul
if not exist "%INSTALL_DIR%\updater.py" ( echo        [WARN] updater.py & set DL_FAIL=1 )

powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%REPO_BASE%/launcher.vbs', '%INSTALL_DIR%\launcher.vbs')" >nul 2>nul
if not exist "%INSTALL_DIR%\launcher.vbs" (
    echo Dim sDir > "%INSTALL_DIR%\launcher.vbs"
    echo sDir = CreateObject^("Scripting.FileSystemObject"^).GetParentFolderName^(WScript.ScriptFullName^) >> "%INSTALL_DIR%\launcher.vbs"
    echo CreateObject^("WScript.Shell"^).Run "pythonw " ^& Chr^(34^) ^& sDir ^& "\main.py" ^& Chr^(34^), 0, False >> "%INSTALL_DIR%\launcher.vbs"
)

powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%REPO_BASE%/updater_launcher.vbs', '%INSTALL_DIR%\updater_launcher.vbs')" >nul 2>nul
if not exist "%INSTALL_DIR%\updater_launcher.vbs" (
    echo Dim sDir > "%INSTALL_DIR%\updater_launcher.vbs"
    echo sDir = CreateObject^("Scripting.FileSystemObject"^).GetParentFolderName^(WScript.ScriptFullName^) >> "%INSTALL_DIR%\updater_launcher.vbs"
    echo CreateObject^("WScript.Shell"^).Run "pythonw " ^& Chr^(34^) ^& sDir ^& "\updater.py" ^& Chr^(34^), 0, False >> "%INSTALL_DIR%\updater_launcher.vbs"
)

powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%REPO_BASE%/UnblockR.ico', '%INSTALL_DIR%\UnblockR.ico')" >nul 2>nul
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://raw.githubusercontent.com/396abc/UnblockR/main/UnblockR.png', '%INSTALL_DIR%\UnblockR.png')" >nul 2>nul

if not exist "%INSTALL_DIR%\settings.json" (
    echo {"window":{"x":120,"y":120,"w":940,"h":620},"disabler_active":false} > "%INSTALL_DIR%\settings.json"
)

if %DL_FAIL% equ 1 (
    echo        [FAIL] Some files could not be downloaded.
    echo        Check your internet connection and try again.
    pause
    exit /b 1
)
echo        Done.

:: Step 4: Create shortcuts
echo.
echo  [4/5] Creating shortcuts...

powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%INSTALL_DIR%\UnblockR.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\""%INSTALL_DIR%\launcher.vbs\""'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.IconLocation = '%INSTALL_DIR%\UnblockR.ico'; $s.Description = 'UnblockR'; $s.Save()" >nul 2>nul

if not exist "%START_MENU%\UnblockR" mkdir "%START_MENU%\UnblockR" >nul 2>nul
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%START_MENU%\UnblockR\UnblockR.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\""%INSTALL_DIR%\launcher.vbs\""'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.IconLocation = '%INSTALL_DIR%\UnblockR.ico'; $s.Description = 'UnblockR'; $s.Save()" >nul 2>nul

echo        Done.

:: Step 5: Launch
echo.
echo  [5/5] Launching UnblockR...

start "" wscript.exe "%INSTALL_DIR%\launcher.vbs"
timeout /t 2 /nobreak >nul

cls
echo  ================================================
echo         UnblockR Installed Successfully
echo  ================================================
echo.
echo    Location : %INSTALL_DIR%
echo    Start Menu: Search "UnblockR" in Start
echo.
echo  ================================================
timeout /t 4 /nobreak >nul
exit /b 0
