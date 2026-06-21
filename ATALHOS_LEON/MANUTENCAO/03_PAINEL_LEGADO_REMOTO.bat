@echo off
title LEON REMOTE CONTROL PANEL

cd /d C:\XAU_ELITE_AI

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set LEON_PANEL_HOST=0.0.0.0
set LEON_PANEL_PORT=8765
set LEON_PANEL_REMOTE_READ_ONLY=true
set /p LEON_PANEL_ACCESS_KEY=Digite uma chave temporaria para acesso remoto: 

python -B src\leon_panel.py

pause
