@echo off
setlocal

set SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\LEON_XAU_AI_STARTUP.lnk

if exist "%SHORTCUT%" (
  del "%SHORTCUT%"
  echo Inicializacao automatica removida.
) else (
  echo Nenhum atalho de inicializacao encontrado.
)

pause
