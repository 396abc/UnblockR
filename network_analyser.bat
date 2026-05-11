@echo off
title UnblockR Diagnostics
echo ===================================================================
echo                  UnblockR Network Diagnostics
echo ===================================================================
echo.

echo [1] DNS RESOLUTION
echo --------------------------------------------------
echo static.unblockr.org:
nslookup static.unblockr.org 2>&1
echo.
echo unblockr.org:
nslookup unblockr.org 2>&1
echo.
echo dash.unblockr.org:
nslookup dash.unblockr.org 2>&1
echo.
echo auth.unblockr.org:
nslookup auth.unblockr.org 2>&1
echo.
echo Direct IP lookup:
nslookup 152.67.99.77 2>&1
echo.

echo [2] PING TESTS
echo --------------------------------------------------
echo Pinging domain:
ping -n 3 static.unblockr.org 2>&1
echo.
echo Pinging IP directly:
ping -n 3 152.67.99.77 2>&1
echo.

echo [3] PORT SCAN - Common Ports
echo --------------------------------------------------
echo Port 80 (HTTP):
curl -v -m 5 http://static.unblockr.org:80 2>&1 | findstr /i "connected refused timeout failed"
echo.
echo Port 443 (HTTPS):
curl -v -m 5 https://static.unblockr.org:443 2>&1 | findstr /i "connected refused timeout failed"
echo.
echo Port 8080 (Alt HTTP):
curl -v -m 5 http://static.unblockr.org:8080 2>&1 | findstr /i "connected refused timeout failed"
echo.
echo Port 3128 (Common proxy):
curl -v -m 5 http://static.unblockr.org:3128 2>&1 | findstr /i "connected refused timeout failed"
echo.
echo Port 8000 (Alt):
curl -v -m 5 http://static.unblockr.org:8000 2>&1 | findstr /i "connected refused timeout failed"
echo.
echo Port 8443 (Alt HTTPS):
curl -v -m 5 https://static.unblockr.org:8443 2>&1 | findstr /i "connected refused timeout failed"
echo.

echo [4] PROXY PORT 8888 - Full Verbose
echo --------------------------------------------------
curl -v -m 10 http://static.unblockr.org:8888 2>&1
echo.
echo --- Direct IP ---
curl -v -m 10 http://152.67.99.77:8888 2>&1
echo.

echo [5] PROXY FUNCTIONALITY
echo --------------------------------------------------
echo Proxy test via domain:
curl -v -m 10 -x http://static.unblockr.org:8888 http://example.com 2>&1
echo.
echo Proxy test via IP:
curl -v -m 10 -x http://152.67.99.77:8888 http://example.com 2>&1
echo.
echo Proxy test HTTPS target:
curl -v -m 10 -x http://static.unblockr.org:8888 https://httpbin.org/ip 2>&1
echo.

echo [6] TRACEROUTE
echo --------------------------------------------------
tracert -d -h 15 -w 2 152.67.99.77 2>&1
echo.

echo [7] SYSTEM PROXY STATE
echo --------------------------------------------------
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable 2>&1
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer 2>&1
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyOverride 2>&1
echo.

echo [8] SERVICE ENDPOINTS
echo --------------------------------------------------
echo Dashboard:
curl -v -m 5 https://dash.unblockr.org/api/stats 2>&1
echo.
echo Auth:
curl -v -m 5 https://auth.unblockr.org/auth/verify?token=test 2>&1
echo.
echo Main site:
curl -v -m 5 https://unblockr.org 2>&1 | findstr /i "HTTP/ UnblockR"
echo.

echo [9] NETWORK ENVIRONMENT
echo --------------------------------------------------
echo Current DNS servers:
ipconfig /all | findstr /i "DNS Servers"
echo.
echo Default gateway:
ipconfig | findstr /i "Default Gateway"
echo.
echo Network adapter info:
ipconfig | findstr /i "IPv4"
echo.

echo [10] FIREWALL CHECK
echo --------------------------------------------------
echo Windows Firewall state:
netsh advfirewall show currentprofile 2>&1 | findstr /i "State"
echo.
echo Outbound rules count:
netsh advfirewall firewall show rule dir=out 2>&1 | findstr /i "Block" | find /c "Block"
echo.

echo [11] CHROME PROXY BYPASS TEST
echo --------------------------------------------------
echo Checking if Chrome has separate proxy settings:
reg query "HKLM\SOFTWARE\Policies\Google\Chrome" /s 2>&1 | findstr /i "proxy"
echo.
reg query "HKCU\SOFTWARE\Policies\Google\Chrome" /s 2>&1 | findstr /i "proxy"
echo.

echo [12] UNBLOCKR APP LOG
echo --------------------------------------------------
if exist "%LOCALAPPDATA%\UnblockR\unblockr.log" (
    type "%LOCALAPPDATA%\UnblockR\unblockr.log" 2>&1
) else (
    echo No log file found.
)
echo.

echo ===================================================================
echo                  DIAGNOSTICS COMPLETE
echo ===================================================================
echo.
echo Look for:
echo  - "Connected" = port is open
echo  - "refused" = port closed on server
echo  - "timed out" = port blocked by network
echo  - "failed" = DNS or connectivity issue
echo  - "Could not resolve" = DNS blocked
echo.
pause
