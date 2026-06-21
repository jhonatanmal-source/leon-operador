@echo off
setlocal

cd /d C:\XAU_ELITE_AI

set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1

if not exist logs mkdir logs

start "LEON PAINEL" /min cmd /c "python -B src\leon_panel.py >> logs\panel_runtime.log 2>> logs\panel_runtime_error.log"
timeout /t 3 /nobreak >nul
start "LEON OPERADOR 24H" /min cmd /c "python -B src\leon_operator.py >> logs\operator_runtime.log 2>> logs\operator_runtime_error.log"

call "%~dp0abrir_codex.bat"

exit /b 0
