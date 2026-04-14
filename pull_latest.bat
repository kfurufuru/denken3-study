@echo off
cd /d "C:\Users\kfuru\.secretary\denken3-study-dashboard"
git pull origin main >> "%~dp0pull_log.txt" 2>&1
