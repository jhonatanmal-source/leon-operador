@echo off
title LEON XAU AI - REMOVER INICIALIZACAO

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP%\LEON XAU AI - Abrir Todo Dia.lnk"

if exist "%SHORTCUT%" (
  del "%SHORTCUT%"
  echo LEON removido da inicializacao do Windows.
) else (
  echo LEON nao estava configurado na inicializacao do Windows.
)

echo.
pause
