@echo off
cd /d C:\Users\yuscr\cali-soul
start /B python cali_bridge.py
timeout /t 3 >nul
echo.
echo   -- cali bridge --
echo   token:
type bridge_token.txt
echo.
echo.
echo   starting tunnel... (url will appear below)
echo.
C:\Users\yuscr\cloudflared.exe tunnel --url http://localhost:9247
