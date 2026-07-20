@echo off
cd /d "C:\Users\kfuru\.secretary\denken3-study-dashboard"
echo ---- pull %date% %time% ---->> "%~dp0pull_log.txt"
git pull --autostash origin main >> "%~dp0pull_log.txt" 2>&1
