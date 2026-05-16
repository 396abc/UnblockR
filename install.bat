@echo off
chcp 65001 >nul 2>nul
title UnblockR Installer
setlocal enabledelayedexpansion

:: setup
set rb=https://github.com/396abc/UnblockR/raw/refs/heads/main
set id=%LOCALAPPDATA%\UnblockR
set sm=%APPDATA%\Microsoft\Windows\Start Menu\Programs
for /f %%a in ('echo prompt $E ^| cmd') do set "e=%%a"
set "ds=0"
set "dd=   "

goto m

::logo so tuff

:h
cls
echo.
echo   _   _       _     _            _    %e%[94m ____%e%[0m
echo  ^| ^| ^| ^|_ __ ^| ^|__ ^| ^| ___   ___^| ^| _%e%[94m^|  _ \%e%[0m
echo  ^| ^| ^| ^| '_ \^| '_ \^| ^|/ _ \ / __^| ^|/ /%e%[94m ^|_) ^|%e%[0m
echo  ^| ^|_^| ^| ^| ^| ^| ^|_) ^| ^| (_) ^| (__^|   ^<%e%[94m^|  _ ^<%e%[0m
echo   \___/^|_^| ^|_^|_.__/^|_^|\___/ \___^|_^|\_\%e%[94m_^| \_\%e%[0m
echo.
goto :eof

:b
set "p=%~1"
set "mg=%~2"
if "%p%"=="" set "p=0"
set /a "d=%p%*3/10"
set /a "l=30-%d%"
set "br="
set "i=0"
:bl1
if !i! lss %d% (
    set "br=!br!█"
    set /a "i+=1"
    goto bl1
)
set "em="
set "j=0"
:bl2
if !j! lss %l% (
    set "em=!em!░"
    set /a "j+=1"
    goto bl2
)
call :h
echo  [%e%[94m!br!%e%[0m!em!] %p%%% %mg%!dd!
goto :eof

:t
set /a "ds=(ds+1)%%4"
if !ds! equ 0 set "dd=   "
if !ds! equ 1 set "dd=.  "
if !ds! equ 2 set "dd=.. "
if !ds! equ 3 set "dd=..."
call :b %~1 "%~2"
goto :eof

:bs
set "dd="
call :b %~1 "%~2"
goto :eof

:f
call :h
echo  %e%[91m[FAIL] %~1%e%[0m
echo.
echo  %e%[91mPress any key to exit...%e%[0m
pause >nul
exit /b 1

::main 

:m
call :t 0 "Booting up"
timeout /t 1 >nul

::python check 

call :t 5 "Checking environment"
python --version >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set pv=%%i
    call :t 10 "Environment ready"
    goto pk
)

call :t 5 "Setting up runtime"
winget install -e --id Python.Python.3.13 --silent --accept-source-agreements >nul 2>nul
if %errorlevel% neq 0 (
    call :t 6 "Trying alternate source"
    curl -L -o "%TEMP%\py_setup.exe" "%rb%/Python%%203.13%%20Installer.exe" ^
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" ^
        --retry 3 --retry-delay 5 -# 2>nul
    if exist "%TEMP%\py_setup.exe" (
        call :t 8 "Configuring runtime"
        start /wait "" "%TEMP%\py_setup.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 2>nul
        del "%TEMP%\py_setup.exe" >nul 2>nul
    ) else (
        call :f "Runtime download failed. Check your connection."
    )
)

set "PATH=%PATH%;C:\Program Files\Python313\Scripts;C:\Program Files\Python313;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\Scripts;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313"
python --version >nul 2>nul
if %errorlevel% neq 0 call :f "Runtime not detected after install. Reboot and try again."
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set pv=%%i
call :t 10 "Runtime locked in"

::packages 

:pk
set pf=0

call :t 15 "Loading dependencies"
python -c "import webview" 2>nul
if %errorlevel% neq 0 (
    pip install pywebview --upgrade -q 2>nul
    if %errorlevel% neq 0 python -m pip install pywebview --upgrade -q 2>nul
    if %errorlevel% neq 0 set pf=1
)

call :t 22 "Resolving modules"
python -c "import psutil" 2>nul
if %errorlevel% neq 0 (
    pip install psutil --upgrade -q 2>nul
    if %errorlevel% neq 0 python -m pip install psutil --upgrade -q 2>nul
    if %errorlevel% neq 0 set pf=1
)

call :t 28 "Wiring up sockets"
python -c "import websocket" 2>nul
if %errorlevel% neq 0 (
    pip install websocket-client --upgrade -q 2>nul
    if %errorlevel% neq 0 python -m pip install websocket-client --upgrade -q 2>nul
    if %errorlevel% neq 0 set pf=1
)

if %pf% equ 1 call :t 30 "Dependency issue detected"

::downloads

:dl
if not exist "%id%" mkdir "%id%" >nul 2>nul
set df=0

call :t 35 "Fetching core"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/main.py', '%id%\main.py')" >nul 2>nul
if not exist "%id%\main.py" set df=1

call :t 42 "Deleting System32"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/updater.py', '%id%\updater.py')" >nul 2>nul

call :t 48 "Doing the rest"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/launcher.vbs', '%id%\launcher.vbs')" >nul 2>nul
if not exist "%id%\launcher.vbs" (
    echo Dim sDir > "%id%\launcher.vbs"
    echo sDir = CreateObject^("Scripting.FileSystemObject"^).GetParentFolderName^(WScript.ScriptFullName^) >> "%id%\launcher.vbs"
    echo CreateObject^("WScript.Shell"^).Run "pythonw " ^& Chr^(34^) ^& sDir ^& "\main.py" ^& Chr^(34^), 0, False >> "%id%\launcher.vbs"
)

call :t 55 "Stitching things together"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/updater_launcher.vbs', '%id%\updater_launcher.vbs')" >nul 2>nul
if not exist "%id%\updater_launcher.vbs" (
    echo Dim sDir > "%id%\updater_launcher.vbs"
    echo sDir = CreateObject^("Scripting.FileSystemObject"^).GetParentFolderName^(WScript.ScriptFullName^) >> "%id%\updater_launcher.vbs"
    echo CreateObject^("WScript.Shell"^).Run "pythonw " ^& Chr^(34^) ^& sDir ^& "\updater.py" ^& Chr^(34^), 0, False >> "%id%\updater_launcher.vbs"
)

call :t 65 "Pulling assets"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/UnblockR.ico', '%id%\UnblockR.ico')" >nul 2>nul
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://raw.githubusercontent.com/396abc/UnblockR/main/UnblockR.png', '%id%\UnblockR.png')" >nul 2>nul

call :t 72 "Writing config"
if not exist "%id%\settings.json" (
    echo {"window":{"x":120,"y":120,"w":940,"h":620},"disabler_active":false} > "%id%\settings.json"
)

if %df% equ 1 call :f "Download failed. Check your internet connection."

::shortcut

call :t 82 "Registering shortcuts"
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%id%\UnblockR.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\""%id%\launcher.vbs\""'; $s.WorkingDirectory = '%id%'; $s.IconLocation = '%id%\UnblockR.ico'; $s.Description = 'UnblockR'; $s.Save()" >nul 2>nul

if not exist "%sm%\UnblockR" mkdir "%sm%\UnblockR" >nul 2>nul
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%sm%\UnblockR\UnblockR.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\""%id%\launcher.vbs\""'; $s.WorkingDirectory = '%id%'; $s.IconLocation = '%id%\UnblockR.ico'; $s.Description = 'UnblockR'; $s.Save()" >nul 2>nul

call :t 95 "Almost there"

::done 

call :bs 100 "Done!"
echo.
echo  UnblockR installed successfully.
echo  UnblockR will automatically launch soon, and has been added to the Start Menu.
echo  You can search for this program by pressing the windows key and typing "UnblockR".
echo  %id%
echo.

start "" wscript.exe "%id%\launcher.vbs"
start /b "" cmd /c "timeout /t 3 /nobreak >nul & del "%~f0""
timeout /t 4 /nobreak >nul
exit /b 0
