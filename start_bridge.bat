@echo off
cd /d C:\Users\yuscr\cali-soul
start /B python cali_bridge.py
timeout /t 2 >nul
C:\Users\yuscr\cloudflared.exe tunnel --url http://localhost:9247
