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
if !dc! equ 0 call :b !rp! "!rmsg!   "
if !dc! equ 1 call :b !rp! "!rmsg!.  "
if !dc! equ 2 call :b !rp! "!rmsg!.. "
if !dc! equ 3 (
    if !elapsed! geq 15 (
        call :b !rp! "!rmsg!..." "Still running, just taking a moment"
    ) else (
        call :b !rp! "!rmsg!..."
    )
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

::manual python install with new window

:install_python
echo Starting Python 3.13 installation in a new window...
echo.
echo IMPORTANT: A new Command Prompt window will open to install Python.
echo Please wait for the installation to complete, then return here and type 'y'
echo.
echo Press any key to open the Python installation window...
pause >nul

:: Create a temporary batch script to run winget in a new window
set "py_install_script=%TEMP%\install_python.bat"
(
echo @echo off
echo title Installing Python 3.13 - Please Wait
echo echo Installing Python 3.13 via winget...
echo echo.
echo winget install -e --id Python.Python.3.13 --silent --accept-source-agreements
echo if !errorlevel! equ 0 ^(
echo     echo.
echo     echo [SUCCESS] Python 3.13 has been installed successfully^^!
echo ^) else ^(
echo     echo.
echo     echo [ERROR] Python installation failed. Please install manually from python.org
echo ^)
echo echo.
echo echo You can close this window now and return to the main installer.
echo timeout /t 5 /nobreak ^>nul
) > "%py_install_script%"

:: Open new cmd window with the installation script
start cmd /k "%py_install_script%"

:: Manual confirmation loop
:wait_for_python
echo.
call :t 10 "Waiting for Python installation..."
echo.
set /p "py_installed=Has Python finished installing? (y/n): "
if /i "!py_installed!"=="y" goto :verify_python
if /i "!py_installed!"=="n" (
    echo Please wait for the Python installation to complete.
    echo Check the other Command Prompt window for progress.
    timeout /t 2 /nobreak >nul
    goto wait_for_python
)
echo Invalid input. Please enter 'y' or 'n'.
goto wait_for_python

:verify_python
call :t 15 "Verifying Python installation..."

:: Update PATH to include Python paths
set "PATH=%PATH%;C:\Program Files\Python313\Scripts;C:\Program Files\Python313;C:\Program Files\Python313\Lib\site-packages\Scripts;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\Scripts;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313"

:: Force refresh environment variables
call refreshenv >nul 2>nul

python --version >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set pv=%%i
    call :t 20 "!pv! ready"
    goto pk
)

:: Try one more time with full path
C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe --version >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe --version 2^>^&1') do set pv=%%i
    set "PATH=%PATH%;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\Scripts"
    call :t 20 "!pv! ready"
    goto pk
)

call :f "Python not detected after install. Please reboot and run the installer again."
goto :eof

::main

:m
call :t 0 "Booting up"
timeout /t 1 >nul

::python check

call :t 5 "Checking for Python"
python --version >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set pv=%%i
    call :t 10 "!pv! found"
    goto pk
)

:: If Python not found, open new window for manual installation
call :install_python

::packages

:pk
set pf=0

call :run 25 "Installing pywebview" "python -c ""import webview"" 2>nul || pip install pywebview --upgrade -q 2>nul || python -m pip install pywebview --upgrade -q 2>nul"

call :run 35 "Installing psutil" "python -c ""import psutil"" 2>nul || pip install psutil --upgrade -q 2>nul || python -m pip install psutil --upgrade -q 2>nul"

call :run 45 "Installing websocket-client" "python -c ""import websocket"" 2>nul || pip install websocket-client --upgrade -q 2>nul || python -m pip install websocket-client --upgrade -q 2>nul"

::downloads

:dl
if not exist "%id%" mkdir "%id%" >nul 2>nul
set df=0

call :run 55 "Downloading application core" "powershell -NoProfile -Command ""[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/main.py', '%id%\main.py')"" >nul 2>nul"
if not exist "%id%\main.py" set df=1

call :run 62 "Downloading updater" "powershell -NoProfile -Command ""[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/updater.py', '%id%\updater.py')"" >nul 2>nul"

call :run 68 "Downloading launchers" "powershell -NoProfile -Command ""[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/launcher.vbs', '%id%\launcher.vbs')"" >nul 2>nul"
if not exist "%id%\launcher.vbs" (
    echo Dim sDir > "%id%\launcher.vbs"
    echo sDir = CreateObject^("Scripting.FileSystemObject"^).GetParentFolderName^(WScript.ScriptFullName^) >> "%id%\launcher.vbs"
    echo CreateObject^("WScript.Shell"^).Run "pythonw " ^& Chr^(34^) ^& sDir ^& "\main.py" ^& Chr^(34^), 0, False >> "%id%\launcher.vbs"
)

call :run 75 "Downloading updater launcher" "powershell -NoProfile -Command ""[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/updater_launcher.vbs', '%id%\updater_launcher.vbs')"" >nul 2>nul"
if not exist "%id%\updater_launcher.vbs" (
    echo Dim sDir > "%id%\updater_launcher.vbs"
    echo sDir = CreateObject^("Scripting.FileSystemObject"^).GetParentFolderName^(WScript.ScriptFullName^) >> "%id%\updater_launcher.vbs"
    echo CreateObject^("WScript.Shell"^).Run "pythonw " ^& Chr^(34^) ^& sDir ^& "\updater.py" ^& Chr^(34^), 0, False >> "%id%\updater_launcher.vbs"
)

call :run 82 "Downloading assets" "powershell -NoProfile -Command ""[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%rb%/UnblockR.ico', '%id%\UnblockR.ico'); (New-Object Net.WebClient).DownloadFile('https://raw.githubusercontent.com/396abc/UnblockR/main/UnblockR.png', '%id%\UnblockR.png')"" >nul 2>nul"

call :t 88 "Writing config"
if not exist "%id%\settings.json" (
    echo {"window":{"x":120,"y":120,"w":940,"h":620},"disabler_active":false} > "%id%\settings.json"
)

if %df% equ 1 call :f "Download failed. Check your internet connection."

::shortcuts

call :run 92 "Creating shortcuts" "powershell -NoProfile -Command ""$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%id%\UnblockR.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\""""%id%\launcher.vbs\""""'; $s.WorkingDirectory = '%id%'; $s.IconLocation = '%id%\UnblockR.ico'; $s.Description = 'UnblockR'; $s.Save()"" >nul 2>nul"

if not exist "%sm%\UnblockR" mkdir "%sm%\UnblockR" >nul 2>nul
call :run 96 "Adding to Start Menu" "powershell -NoProfile -Command ""$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%sm%\UnblockR\UnblockR.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\""""%id%\launcher.vbs\""""'; $s.WorkingDirectory = '%id%'; $s.IconLocation = '%id%\UnblockR.ico'; $s.Description = 'UnblockR'; $s.Save()"" >nul 2>nul"

call :t 100 "Almost there"

::done

call :t 100 "Done!"
echo.
echo  UnblockR installed successfully!
echo  UnblockR will automatically launch soon, and has been added to the Start Menu.
echo  You can search for this program by pressing the windows key and typing "UnblockR".
echo  Installation path: %id%
echo.

start "" wscript.exe "%id%\launcher.vbs"

:: Cleanup
set "py_install_script="
timeout /t 4 /nobreak >nul
exit /b 0
