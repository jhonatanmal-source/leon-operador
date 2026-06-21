@echo off
title LEON XAU AI - INICIALIZACAO WINDOWS

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP%\LEON XAU AI - Abrir Todo Dia.lnk"
set "TARGET=C:\XAU_ELITE_AI\LEON_TODOS_OS_DIAS\01_ABRIR_LEON_TODO_DIA.bat"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$shell = New-Object -ComObject WScript.Shell;" ^
  "$shortcut = $shell.CreateShortcut('%SHORTCUT%');" ^
  "$shortcut.TargetPath = '%TARGET%';" ^
  "$shortcut.WorkingDirectory = 'C:\XAU_ELITE_AI';" ^
  "$shortcut.IconLocation = 'C:\Windows\System32\shell32.dll,44';" ^
  "$shortcut.Save()"

echo.
echo LEON foi colocado na inicializacao do Windows.
echo Quando o computador ligar, o LEON abrira automaticamente.
echo.
pause
