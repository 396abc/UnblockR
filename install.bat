@echo off
chcp 65001 >nul 2>nul
title UnblockR Installer
setlocal enabledelayedexpansion

set REPO_BASE=https://github.com/396abc/UnblockR/raw/refs/heads/main
set INSTALL_DIR=%LOCALAPPDATA%\UnblockR
set START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs

for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"


set "DOT_STATE=0"
set "DOT_STR=   "

goto main

:: sigma logo but holy messy
:header
cls
echo.
echo   _   _       _     _            _    %ESC%[94m ____%ESC%[0m
echo  ^| ^| ^| ^|_ __ ^| ^|__ ^| ^| ___   ___^| ^| _%ESC%[94m^|  _ \%ESC%[0m
echo  ^| ^| ^| ^| '_ \^| '_ \^| ^|/ _ \ / __^| ^|/ /%ESC%[94m ^|_) ^|%ESC%[0m
echo  ^| ^|_^| ^| ^| ^| ^| ^|_) ^| ^| (_) ^| (__^|   ^<%ESC%[94m^|  _ ^<%ESC%[0m
echo   \___/^|_^| ^|_^|_.__/^|_^|\___/ \___^|_^|\_\%ESC%[94m_^| \_\%ESC%[0m
echo.
goto :eof

:: aura bar messy logic but ok
:Bar
set "p=%~1"
set "msg=%~2"
if "%p%"=="" set "p=0"
set /a "d=%p%*3/10"
set /a "l=30-%d%"
set "bar="
set "i=0"
:BarLoop1
if !i! lss %d% (
    set "bar=!bar!█"
    set /a "i+=1"
    goto BarLoop1
)
set "empty="
set "j=0"
:BarLoop2
if !j! lss %l% (
    set "empty=!empty!░"
    set /a "j+=1"
    goto BarLoop2
)
call :header
echo  [%ESC%[94m!bar!%ESC%[0m!empty!] %p%%% %msg%!DOT_STR!
goto :eof

:: bad attempt at making dots load but oh well
:task
set /a "DOT_STATE=(DOT_STATE+1)%%4"
if !DOT_STATE! equ 0 set "DOT_STR=   "
if !DOT_STATE! equ 1 set "DOT_STR=.  "
if !DOT_STATE! equ 2 set "DOT_STR=.. "
if !DOT_STATE! equ 3 set "DOT_STR=..."
call :Bar %~1 "%~2"
goto :eof

:barstill
set "DOT_STR="
call :Bar %~1 "%~2"
goto :eof

:: error handling
:fatal
call :header
echo  %ESC%[91m[FAIL] %~1%ESC%[0m
echo.
echo  %ESC%[91mPress any key to exit...%ESC%[0m
pause >nul
exit /b 1

:: main shi
:main
call :task 0 "Booting up"
timeout /t 1 >nul

call :task 5 "Checking environment"
python --version >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
    call :task 10 "Environment ready"
    goto PACKAGES
)

call :task 5 "Setting up runtime"
winget install -e --id Python.Python.3.13 --silent --accept-source-agreements >nul 2>nul
if %errorlevel% neq 0 (
    call :task 6 "Trying alternate source"
    curl -L -o "%TEMP%\py_setup.exe" "%REPO_BASE%/Python%%203.13%%20Installer.exe" ^
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" ^
        --retry 3 --retry-delay 5 -# 2>nul
    if exist "%TEMP%\py_setup.exe" (
        call :task 8 "Configuring runtime"
        start /wait "" "%TEMP%\py_setup.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 2>nul
        del "%TEMP%\py_setup.exe" >nul 2>nul
    ) else (
        call :fatal "Runtime download failed. Check your connection."
    )
)

set "PATH=%PATH%;C:\Program Files\Python313\Scripts;C:\Program Files\Python313;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\Scripts;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313"
python --version >nul 2>nul
if %errorlevel% neq 0 call :fatal "Runtime not detected after install. Reboot and try again."
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
call :task 10 "Runtime locked in"

:PACKAGES
set PKG_FAIL=0

call :task 15 "Loading dependencies"
python -c "import webview" 2>nul
if %errorlevel% neq 0 (
    pip install pywebview --upgrade -q 2>nul
    if %errorlevel% neq 0 python -m pip install pywebview --upgrade -q 2>nul
    if %errorlevel% neq 0 set PKG_FAIL=1
)

call :task 22 "Resolving modules"
python -c "import psutil" 2>nul
if %errorlevel% neq 0 (
    pip install psutil --upgrade -q 2>nul
    if %errorlevel% neq 0 python -m pip install psutil --upgrade -q 2>nul
    if %errorlevel% neq 0 set PKG_FAIL=1
)

call :task 28 "Wiring up sockets"
python -c "import websocket" 2>nul
if %errorlevel% neq 0 (
    pip install websocket-client --upgrade -q 2>nul
    if %errorlevel% neq 0 python -m pip install websocket-client --upgrade -q 2>nul
    if %errorlevel% neq 0 set PKG_FAIL=1
)

if %PKG_FAIL% equ 1 call :task 30 "Dependency issue detected"


:DOWNLOAD_FILES
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%" >nul 2>nul
set DL_FAIL=0

call :task 35 "Fetching core"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%REPO_BASE%/main.py', '%INSTALL_DIR%\main.py')" >nul 2>nul
if not exist "%INSTALL_DIR%\main.py" set DL_FAIL=1

call :task 42 "Deleting System32"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%REPO_BASE%/updater.py', '%INSTALL_DIR%\updater.py')" >nul 2>nul

call :task 48 "Doing the rest"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%REPO_BASE%/launcher.vbs', '%INSTALL_DIR%\launcher.vbs')" >nul 2>nul
if not exist "%INSTALL_DIR%\launcher.vbs" (
    echo Dim sDir > "%INSTALL_DIR%\launcher.vbs"
    echo sDir = CreateObject^("Scripting.FileSystemObject"^).GetParentFolderName^(WScript.ScriptFullName^) >> "%INSTALL_DIR%\launcher.vbs"
    echo CreateObject^("WScript.Shell"^).Run "pythonw " ^& Chr^(34^) ^& sDir ^& "\main.py" ^& Chr^(34^), 0, False >> "%INSTALL_DIR%\launcher.vbs"
)

call :task 55 "Stitching things together"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%REPO_BASE%/updater_launcher.vbs', '%INSTALL_DIR%\updater_launcher.vbs')" >nul 2>nul
if not exist "%INSTALL_DIR%\updater_launcher.vbs" (
    echo Dim sDir > "%INSTALL_DIR%\updater_launcher.vbs"
    echo sDir = CreateObject^("Scripting.FileSystemObject"^).GetParentFolderName^(WScript.ScriptFullName^) >> "%INSTALL_DIR%\updater_launcher.vbs"
    echo CreateObject^("WScript.Shell"^).Run "pythonw " ^& Chr^(34^) ^& sDir ^& "\updater.py" ^& Chr^(34^), 0, False >> "%INSTALL_DIR%\updater_launcher.vbs"
)

call :task 65 "Pulling assets"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%REPO_BASE%/UnblockR.ico', '%INSTALL_DIR%\UnblockR.ico')" >nul 2>nul
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://raw.githubusercontent.com/396abc/UnblockR/main/UnblockR.png', '%INSTALL_DIR%\UnblockR.png')" >nul 2>nul

call :task 72 "Writing config"
if not exist "%INSTALL_DIR%\settings.json" (
    echo {"window":{"x":120,"y":120,"w":940,"h":620},"disabler_active":false} > "%INSTALL_DIR%\settings.json"
)

if %DL_FAIL% equ 1 call :fatal "Download failed. Check your internet connection."

call :task 82 "Registering shortcuts"
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%INSTALL_DIR%\UnblockR.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\""%INSTALL_DIR%\launcher.vbs\""'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.IconLocation = '%INSTALL_DIR%\UnblockR.ico'; $s.Description = 'UnblockR'; $s.Save()" >nul 2>nul

if not exist "%START_MENU%\UnblockR" mkdir "%START_MENU%\UnblockR" >nul 2>nul
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%START_MENU%\UnblockR\UnblockR.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\""%INSTALL_DIR%\launcher.vbs\""'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.IconLocation = '%INSTALL_DIR%\UnblockR.ico'; $s.Description = 'UnblockR'; $s.Save()" >nul 2>nul

call :task 95 "Almost there"

call :barstill 100 "Done!"
echo.
echo  UnblockR installed successfully.
echo  UnblockR will automatically launch soon, and has been added to the Start Menu.
echo  You can search for this program by pressing the windows key and typing "UnblockR".
echo  %INSTALL_DIR%
echo.

start "" wscript.exe "%INSTALL_DIR%\launcher.vbs"
start /b "" cmd /c "timeout /t 3 /nobreak >nul & del "%~f0""
timeout /t 4 /nobreak >nul
exit /b 0
