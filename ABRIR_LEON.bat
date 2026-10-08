@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" scripts\local_control.py start
if errorlevel 1 pause
start "" "http://127.0.0.1:5055/login"
