@echo off
title LEON XAU AI - OPERADOR

cd /d C:\XAU_ELITE_AI

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root='C:\XAU_ELITE_AI';" ^
  "$operator=Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*leon_operator.py*' -and $_.CommandLine -notlike '*--grant-autonomy*' -and $_.CommandLine -notlike '*--send-status*' };" ^
  "if (-not $operator) { Start-Process -FilePath python -ArgumentList '-B','src\leon_operator.py' -WorkingDirectory $root -WindowStyle Hidden }"

echo Operador LEON ligado em segundo plano.
pause
