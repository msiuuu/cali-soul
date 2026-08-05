@echo off
cd /d C:\Users\yuscr\cali-soul
echo.
echo   starting bridge...
start /B python cali_bridge.py
timeout /t 2 >nul
echo   bridge up. starting tunnel...
python start_tunnel.py
