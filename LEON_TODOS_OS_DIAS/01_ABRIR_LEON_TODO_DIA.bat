@echo off
title LEON XAU AI - ABRIR TODO DIA

cd /d C:\XAU_ELITE_AI

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ========================================
echo LEON XAU AI - INICIO DIARIO
echo ========================================
echo.
echo Ligando painel, operador e autonomia...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root='C:\XAU_ELITE_AI';" ^
  "$panel=Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*leon_panel.py*' };" ^
  "if (-not $panel) { Start-Process -FilePath python -ArgumentList '-B','src\leon_panel.py' -WorkingDirectory $root -WindowStyle Hidden };" ^
  "$operator=Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*leon_operator.py*' -and $_.CommandLine -notlike '*--grant-autonomy*' -and $_.CommandLine -notlike '*--send-status*' };" ^
  "if (-not $operator) { Start-Process -FilePath python -ArgumentList '-B','src\leon_operator.py' -WorkingDirectory $root -WindowStyle Hidden }"

python -B src\leon_operator.py --grant-autonomy-minutes 480
python -B src\leon_operator.py --send-status --force

start http://127.0.0.1:8765/

echo.
echo LEON iniciado.
echo Painel: http://127.0.0.1:8765/
echo Telegram: checkpoint enviado.
echo Autonomia: 8 horas.
echo.
echo Pode fechar esta janela. O painel e operador continuam em segundo plano.
pause
