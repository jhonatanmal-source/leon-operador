@echo off
setlocal

set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set TARGET=C:\XAU_ELITE_AI\LEON_TODOS_OS_DIAS\08_INICIAR_LEON_E_CODEX.bat
set SHORTCUT=%STARTUP%\LEON_XAU_AI_STARTUP.lnk

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath='%TARGET%'; $s.WorkingDirectory='C:\XAU_ELITE_AI'; $s.WindowStyle=7; $s.Description='Inicia LEON XAU AI, painel, operador e Codex'; $s.Save()"

echo LEON configurado para iniciar com o Windows.
echo Atalho criado em:
echo %SHORTCUT%
pause
