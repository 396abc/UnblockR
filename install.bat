@echo off
chcp 437 >nul 2>nul
title UnblockR Installer
setlocal enabledelayedexpansion

:: setup
set rb=https://github.com/396abc/UnblockR/raw/refs/heads/main
set ro=396abc
set rn=UnblockR
set rr=main
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
    set "br=!br!#"
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
exit

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

set "pypath="
if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe" set "pypath=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313"
if exist "C:\Program Files\Python313\python.exe" set "pypath=C:\Program Files\Python313"
if not defined pypath call :f "Python not detected after install. Reboot and try again."
set "PATH=!pypath!;!pypath!\Scripts;%PATH%"
for /f "tokens=*" %%i in ('"!pypath!\python.exe" --version 2^>^&1') do set pv=%%i
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

call :t 42 "Preparing download"

echo aW1wb3J0IHVybGxpYi5yZXF1ZXN0LGpzb24sdGltZSxvcyxzeXMKdD1zdHIoaW50KHRpbWUudGltZSgpKSkKb3duZXI9c3lzLmFyZ3ZbMV0KcmVwbz1zeXMuYXJndlsyXQpicmFuY2g9c3lzLmFyZ3ZbM10KcmVxPXVybGxpYi5yZXF1ZXN0LlJlcXVlc3QoCiAgICBmImh0dHBzOi8vYXBpLmdpdGh1Yi5jb20vcmVwb3Mve293bmVyfS97cmVwb30vZ2l0L3RyZWVzL3ticmFuY2h9P3JlY3Vyc2l2ZT0xJnQ9e3R9IiwKICAgIGhlYWRlcnM9eyJVc2VyLUFnZW50IjoiVUJSIn0KKQp0cmVlPWpzb24ubG9hZHModXJsbGliLnJlcXVlc3QudXJsb3BlbihyZXEsdGltZW91dD0zMCkucmVhZCgpKQpleGNfdXJsPWYiaHR0cHM6Ly9naXRodWIuY29tL3tvd25lcn0ve3JlcG99L3Jhdy9yZWZzL2hlYWRzL3ticmFuY2h9L3VwZC5leGNsdXNpb25zP3Q9e3R9IgpleGM9e2wuc3RyaXAoKSBmb3IgbCBpbiB1cmxsaWIucmVxdWVzdC51cmxvcGVuKGV4Y191cmwsdGltZW91dD0xNSkucmVhZCgpLmRlY29kZSgpLnNwbGl0bGluZXMoKSBpZiBsLnN0cmlwKCkgYW5kIG5vdCBsLnN0cmlwKCkuc3RhcnRzd2l0aCgiIyIpfQpvdXQ9b3Blbihvcy5wYXRoLmpvaW4ob3MuZW52aXJvblsiVEVNUCJdLCJ1YnJfZmlsZXMudHh0IiksInciKQpmb3IgaSBpbiB0cmVlWyJ0cmVlIl06CiAgICBpZiBpWyJ0eXBlIl0hPSJibG9iIjoKICAgICAgICBjb250aW51ZQogICAgcD1pWyJwYXRoIl07cGFydHM9cC5zcGxpdCgiLyIpO3NraXA9RmFsc2UKICAgIGZvciBlIGluIGV4YzoKICAgICAgICBpZiBwPT1lIG9yIHBhcnRzWy0xXT09ZSBvciBlIGluIHBhcnRzWzotMV06c2tpcD1UcnVlO2JyZWFrCiAgICBpZiBub3Qgc2tpcDpvdXQud3JpdGUocCsiXG4iKQpvdXQuY2xvc2UoKQo= > "%TEMP%\ubr_fetch.b64"
certutil -decode "%TEMP%\ubr_fetch.b64" "%TEMP%\ubr_fetch.py" >nul 2>nul

echo aW1wb3J0IHVybGxpYi5yZXF1ZXN0LHRpbWUsc3lzLG9zCnQ9c3RyKGludCh0aW1lLnRpbWUoKSkpCnVybD1zeXMuYXJndlsxXSsiP3Q9Iit0CmRlc3Q9c3lzLmFyZ3ZbMl0Kb3MubWFrZWRpcnMob3MucGF0aC5kaXJuYW1lKG9zLnBhdGguYWJzcGF0aChkZXN0KSksZXhpc3Rfb2s9VHJ1ZSkKdXJsbGliLnJlcXVlc3QudXJscmV0cmlldmUodXJsLGRlc3QpCg== > "%TEMP%\ubr_dl.b64"
certutil -decode "%TEMP%\ubr_dl.b64" "%TEMP%\ubr_dl.py" >nul 2>nul

call :run 44 "Fetching file list" "python ""%TEMP%\ubr_fetch.py"" %ro% %rn% %rr%"

if not exist "%TEMP%\ubr_files.txt" call :f "Failed to fetch file list. Check your internet connection."

set "fc=0"
for /f "usebackq delims=" %%a in ("%TEMP%\ubr_files.txt") do set /a "fc+=1"
if !fc! equ 0 call :f "No files to download. Check your internet connection."

set "fi=0"
for /f "usebackq delims=" %%a in ("%TEMP%\ubr_files.txt") do (
    set /a "fi+=1"
    set /a "pct=45+fi*35/fc"
    set "fp=%%a"
    set "fp=!fp:/=\!"
    call :run !pct! "Downloading application files" "python ""%TEMP%\ubr_dl.py"" ""https://raw.githubusercontent.com/%ro%/%rn%/%rr%/%%a"" ""%id%\!fp!"""
)

del "%TEMP%\ubr_files.txt" >nul 2>nul
del "%TEMP%\ubr_fetch.py" >nul 2>nul
del "%TEMP%\ubr_fetch.b64" >nul 2>nul
del "%TEMP%\ubr_dl.py" >nul 2>nul
del "%TEMP%\ubr_dl.b64" >nul 2>nul

if not exist "%id%\main.py" call :f "Download failed. Check your internet connection."
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
