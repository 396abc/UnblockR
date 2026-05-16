@echo off
chcp 437 >nul 2>nul
title UnblockR Installer
setlocal enabledelayedexpansion

:: setup
set rb=https://github.com/396abc/UnblockR/raw/refs/heads/main
set id=%LOCALAPPDATA%\UnblockR
set sm=%APPDATA%\Microsoft\Windows\Start Menu\Programs
for /f "delims=" %%a in ('forfiles /p "%~dp0." /m "%~nx0" /c "cmd /c echo 0x1B"') do set "e=%%a"

:: Prevent multiple instances
set "installer_flag=%TEMP%\ubr_installer_running.flag"
if exist "%installer_flag%" (
    exit /b 0
)
echo %DATE% %TIME% > "%installer_flag%"

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

::run background command WITH WAIT

:run_wait
set "rp=%~1"
set "rmsg=%~2"
set "rcmd=%~3"
set "dflag=%TEMP%\ubr_done.flag"
del "%dflag%" >nul 2>nul
start /b "" cmd /c "%rcmd% & echo done > "%dflag%""
set "dc=0"
set "elapsed=0"
set "slowmsg=0"
:runloop
if exist "%dflag%" (
    del "%dflag%" >nul 2>nul
    goto :eof
)
set /a "dc=(dc+1)%%4"
set /a "elapsed+=1"
if !elapsed! geq 15 (
    if !slowmsg! equ 0 (
        set "slowmsg=1"
        call :b !rp! "!rmsg!..." "Still running, just taking a moment"
    ) else (
        if !dc! equ 0 call :b !rp! "!rmsg!   " "Still running, just taking a moment"
        if !dc! equ 1 call :b !rp! "!rmsg!.  " "Still running, just taking a moment"
        if !dc! equ 2 call :b !rp! "!rmsg!.. " "Still running, just taking a moment"
        if !dc! equ 3 call :b !rp! "!rmsg!..." "Still running, just taking a moment"
    )
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
timeout /t 1 /nobreak >nul
goto :eof

::error

:f
call :h
echo  !e![91m[FAIL] %~1!e![0m
echo.
echo  !e![91mPress any key to exit...!e![0m
pause >nul
del "%installer_flag%" >nul 2>nul
exit /b 1

::install python automatically

:install_python_auto
call :t 5 "Python not found. Installing Python 3.13..."
echo.
echo Installing Python 3.13 via winget. This may take a moment...
winget install -e --id Python.Python.3.13 --accept-source-agreements --silent
timeout /t 3 /nobreak >nul
set "PATH=%PATH%;C:\Program Files\Python313\Scripts;C:\Program Files\Python313;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\Scripts;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313"
python --version >nul 2>nul
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set pv=%%i
    call :t 15 "!pv! installed successfully"
    goto :eof
)
call :f "Python installation failed. Please install Python 3.13 manually"
goto :eof

::main

:m
call :t 0 "Booting up"

call :t 3 "Checking for Python"
python --version >nul 2>nul
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set pv=%%i
    call :t 10 "!pv! found"
) else (
    call :install_python_auto
)

::packages
call :run_wait 20 "Installing pywebview" "python -c \"import webview\" 2>nul || pip install pywebview --upgrade -q"
call :run_wait 30 "Installing psutil" "python -c \"import psutil\" 2>nul || pip install psutil --upgrade -q"
call :run_wait 40 "Installing websocket-client" "python -c \"import websocket\" 2>nul || pip install websocket-client --upgrade -q"

::downloads
if not exist "%id%" mkdir "%id%" >nul 2>nul
set df=0

call :run_wait 50 "Downloading main.py" "powershell -Command \"Invoke-WebRequest -Uri '%rb%/main.py' -OutFile '%id%\main.py'\""
if not exist "%id%\main.py" set df=1

call :run_wait 57 "Downloading updater.py" "powershell -Command \"Invoke-WebRequest -Uri '%rb%/updater.py' -OutFile '%id%\updater.py'\""

call :run_wait 63 "Downloading launcher.vbs" "powershell -Command \"Invoke-WebRequest -Uri '%rb%/launcher.vbs' -OutFile '%id%\launcher.vbs'\""
if not exist "%id%\launcher.vbs" (
    echo Dim sDir > "%id%\launcher.vbs"
    echo sDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) >> "%id%\launcher.vbs"
    echo CreateObject("WScript.Shell").Run "pythonw " ^& Chr(34) ^& sDir ^& "\main.py" ^& Chr(34), 0, False >> "%id%\launcher.vbs"
)

call :run_wait 70 "Downloading updater_launcher.vbs" "powershell -Command \"Invoke-WebRequest -Uri '%rb%/updater_launcher.vbs' -OutFile '%id%\updater_launcher.vbs'\""
if not exist "%id%\updater_launcher.vbs" (
    echo Dim sDir > "%id%\updater_launcher.vbs"
    echo sDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) >> "%id%\updater_launcher.vbs"
    echo CreateObject("WScript.Shell").Run "pythonw " ^& Chr(34) ^& sDir ^& "\updater.py" ^& Chr(34), 0, False >> "%id%\updater_launcher.vbs"
)

call :run_wait 78 "Downloading assets" "powershell -Command \"Invoke-WebRequest -Uri '%rb%/UnblockR.ico' -OutFile '%id%\UnblockR.ico'; Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/396abc/UnblockR/main/UnblockR.png' -OutFile '%id%\UnblockR.png'\""

call :t 85 "Writing config"
if not exist "%id%\settings.json" (
    echo {"window":{"x":120,"y":120,"w":940,"h":620},"disabler_active":false} > "%id%\settings.json"
)
if %df% equ 1 call :f "Download failed. Check your internet connection."

::shortcuts
call :run_wait 90 "Creating shortcuts" "powershell -Command \"$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%id%\UnblockR.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%id%\launcher.vbs\"'; $s.WorkingDirectory = '%id%'; $s.IconLocation = '%id%\UnblockR.ico'; $s.Save()\""

if not exist "%sm%\UnblockR" mkdir "%sm%\UnblockR" >nul 2>nul
call :run_wait 95 "Adding to Start Menu" "powershell -Command \"$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%sm%\UnblockR\UnblockR.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%id%\launcher.vbs\"'; $s.WorkingDirectory = '%id%'; $s.IconLocation = '%id%\UnblockR.ico'; $s.Save()\""

::done
call :t 100 "Complete!"
timeout /t 2 /nobreak >nul

call :h
echo.
echo  !e![92mUnblockR installed successfully!!e![0m
echo.
echo  !e![96mThe application will launch in 3 seconds!e![0m
echo  !e![90mYou can also find it in the Start Menu by typing "UnblockR"!e![0m
echo.
echo  !e![90mInstallation path: %id%!e![0m
echo.
timeout /t 3 /nobreak >nul

start "" wscript.exe "%id%\launcher.vbs"
del "%installer_flag%" >nul 2>nul
exit /b 0
