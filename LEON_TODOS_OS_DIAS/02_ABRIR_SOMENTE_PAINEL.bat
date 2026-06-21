@echo off
title LEON XAU AI - PAINEL

cd /d C:\XAU_ELITE_AI

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root='C:\XAU_ELITE_AI';" ^
  "$panel=Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*leon_panel.py*' };" ^
  "if (-not $panel) { Start-Process -FilePath python -ArgumentList '-B','src\leon_panel.py' -WorkingDirectory $root -WindowStyle Hidden }"

start http://127.0.0.1:8765/

echo Painel aberto em http://127.0.0.1:8765/
pause
