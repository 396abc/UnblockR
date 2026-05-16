@echo off
chcp 437 >nul 2>nul
title UnblockR Installer
setlocal enabledelayedexpansion

:: setup
set rb=https://github.com/396abc/UnblockR/raw/refs/heads/main
set id=%LOCALAPPDATA%\UnblockR
set sm=%APPDATA%\Microsoft\Windows\Start Menu\Programs
for /f "delims=" %%a in ('forfiles /p "%~dp0." /m "%~nx0" /c "cmd /c echo 0x1B"') do set "e=%%a"

goto m

::header

:h
cls
echo.
echo   _   _       _     _            _    !e![94m ____!e![0m
echo  ^| ^| ^| ^|_ __ ^| ^|__ ^| ^| ___   ___^| ^| _!e![94m^|  _ \!e![0m
echo  ^| ^| ^| ^| '_ \^| '_ \^| ^|/ _ \ / __^| ^|/ /!e![94m ^|_) ^|!e![0m
echo  ^| ^|_^| ^| ^| ^| ^| ^|_) ^| ^| (_) ^| (__^|   ^<!e![94m^|  _ ^<!e![0m
echo   \___/^|_^| ^|_^|_.__/^|_^|\___/ \___^|_^|\_\!e![94m_^| \_\!e![0m
echo.
goto :eof

::draw bar

:b
set "p=%~1"
set "mg=%~2"
set "xt=%~3"
if "%p%"=="" set "p=0"
set /a "d=%p%*3/10"
set /a "l=30-%d%"
set "br="
set "i=0"
:bl1
if !i! lss %d% (
    set "br=!br!="
    set /a "i+=1"
    goto bl1
)
set "em="
set "j=0"
:bl2
if !j! lss %l% (
    set "em=!em! "
    set /a "j+=1"
    goto bl2
)
call :h
echo  [!e![94m!br!!e![0m!em!] %p%%% %mg%
if defined xt echo.
if defined xt echo  !e![90m!xt!!e![0m
goto :eof

::run background command with animated dots

:run
set "rp=%~1"
set "rmsg=%~2"
set "rcmd=%~3"
set "dflag=%TEMP%\ubr_done.flag"
del "%dflag%" >nul 2>nul
start /b "" cmd /c "%rcmd% & echo done > "%dflag%""
set "dc=0"
set "elapsed=0"
:runloop
if exist "%dflag%" (
    del "%dflag%" >nul 2>nul
    goto :eof
)
set /a "dc=(dc+1)%%4"
set /a "elapsed+=1"
if !elapsed! geq 15 (
    if !dc! equ 0 call :b !rp! "!rmsg!   " "Still running, just taking a moment"
    if !dc! equ 1 call :b !rp! "!rmsg!.  " "Still running, just taking a moment"
    if !dc! equ 2 call :b !rp! "!rmsg!.. " "Still running, just taking a moment"
    if !dc! equ 3 call :b !rp! "!rmsg!..." "Still running, just taking a moment"
) else (
    if !dc! equ 0 call :b !rp! "!rmsg!   "
    if !dc! equ 1 call :b !rp! "!rmsg!.  "
    if !dc! equ 2 call :b !rp! "!rmsg!.. "
    if !dc! equ 3 call :b !rp! "!rmsg!..."
)
timeout /t 1 /nobreak >nul
goto runloop

::simple task

:t
call :b %~1 "%~2"
goto :eof

::error

:f
call :h
echo  !e![91m[FAIL] %~1!e![0m
echo.
echo  !e![91mPress any key to exit...!e![0m
pause >nul
exit /b 1

::main

:m
call :t 0 "Booting up"
timeout /t 1 >nul

::python check

call :t 5 "Checking for Python"
python --version >nul 2>nul
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set pv=%%i
    call :t 10 "!pv! found"
    goto pk
)

::python install

call :run 8 "Installing Python via winget" "winget install -e --id Python.Python.3.13 --silent --accept-source-agreements >nul 2>nul"

set "PATH=%PATH%;C:\Program Files\Python313\Scripts;C:\Program Files\Python313;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\Scripts;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313"

python --version >nul 2>nul
if !errorlevel! neq 0 call :f "Python not detected after install. Reboot and try again."
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set pv=%%i
call :t 15 "!pv! installed"
::packages

:pk
set pf=0

call :run 20 "Installing pywebview" "python -c ""import webview"" 2>nul || pip install pywebview --upgrade -q 2>nul || python -m pip install pywebview --upgrade -q 2>nul"

call :run 30 "Installing psutil" "python -c ""import psutil"" 2>nul || pip install psutil --upgrade -q 2>nul || python -m pip install psutil --upgrade -q 2>nul"

call :run 38 "Installing websocket-client" "python -c ""import websocket"" 2>nul || pip install websocket-client --upgrade -q 2>nul || python -m pip install websocket-client --upgrade -q 2>nul"

::downloads

:dl
if not exist "%id%" mkdir "%id%" >nul 2>nul
set df=0

call :run 45 "Downloading application core" "powershell -NoProfile -Command ""[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/main.py', '%id%\main.py')"" >nul 2>nul"
if not exist "%id%\main.py" set df=1

call :run 52 "Downloading updater" "powershell -NoProfile -Command ""[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/updater.py', '%id%\updater.py')"" >nul 2>nul"

call :run 58 "Downloading application assets" "powershell -NoProfile -Command ""[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/launcher.vbs', '%id%\launcher.vbs')"" >nul 2>nul"
if not exist "%id%\launcher.vbs" (
    echo Dim sDir > "%id%\launcher.vbs"
    echo sDir = CreateObject^("Scripting.FileSystemObject"^).GetParentFolderName^(WScript.ScriptFullName^) >> "%id%\launcher.vbs"
    echo CreateObject^("WScript.Shell"^).Run "pythonw " ^& Chr^(34^) ^& sDir ^& "\main.py" ^& Chr^(34^), 0, False >> "%id%\launcher.vbs"
)

call :run 65 "Downloading application assets" "powershell -NoProfile -Command ""[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/updater_launcher.vbs', '%id%\updater_launcher.vbs')"" >nul 2>nul"
if not exist "%id%\updater_launcher.vbs" (
    echo Dim sDir > "%id%\updater_launcher.vbs"
    echo sDir = CreateObject^("Scripting.FileSystemObject"^).GetParentFolderName^(WScript.ScriptFullName^) >> "%id%\updater_launcher.vbs"
    echo CreateObject^("WScript.Shell"^).Run "pythonw " ^& Chr^(34^) ^& sDir ^& "\updater.py" ^& Chr^(34^), 0, False >> "%id%\updater_launcher.vbs"
)

call :run 75 "Downloading application assets" "powershell -NoProfile -Command ""[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/UnblockR.ico', '%id%\UnblockR.ico'); (New-Object Net.WebClient).DownloadFile('https://raw.githubusercontent.com/396abc/UnblockR/main/UnblockR.png', '%id%\UnblockR.png')"" >nul 2>nul"

call :t 80 "Writing config"
if not exist "%id%\settings.json" (
    echo {"window":{"x":120,"y":120,"w":940,"h":620},"disabler_active":false} > "%id%\settings.json"
)

if %df% equ 1 call :f "Download failed. Check your internet connection."

::shortcuts

call :run 85 "Creating shortcuts" "powershell -NoProfile -Command ""$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%id%\UnblockR.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\""""%id%\launcher.vbs\""""'; $s.WorkingDirectory = '%id%'; $s.IconLocation = '%id%\UnblockR.ico'; $s.Description = 'UnblockR'; $s.Save()"" >nul 2>nul"

if not exist "%sm%\UnblockR" mkdir "%sm%\UnblockR" >nul 2>nul
call :run 92 "Adding to Start Menu" "powershell -NoProfile -Command ""$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%sm%\UnblockR\UnblockR.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\""""%id%\launcher.vbs\""""'; $s.WorkingDirectory = '%id%'; $s.IconLocation = '%id%\UnblockR.ico'; $s.Description = 'UnblockR'; $s.Save()"" >nul 2>nul"

call :t 98 "Almost there"

::done

call :t 100 "Done!"
echo.
echo  UnblockR installed successfully.
echo  UnblockR will automatically launch soon, and has been added to the Start Menu.
echo  You can search for this program by pressing the windows key and typing "UnblockR".
echo  %id%
echo.

start "" wscript.exe "%id%\launcher.vbs"
echo Set s=CreateObject^("WScript.Shell"^) > "%TEMP%\ubr_cleanup.vbs"
echo s.Run "cmd /c ping 127.0.0.1 -n 4 >nul ^& del """ ^& WScript.Arguments^(0^) ^& """", 0, False >> "%TEMP%\ubr_cleanup.vbs"
wscript.exe "%TEMP%\ubr_cleanup.vbs" "%~f0"
timeout /t 4 /nobreak >nul
exit /b 0
