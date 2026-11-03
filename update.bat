@echo off
rem Monthly update: put the IBKR "holdings" and "trades" CSV exports in exports\ first.
rem Optional: update.bat --watch
cd /d "%~dp0"
python scripts\update.py %*
pause
