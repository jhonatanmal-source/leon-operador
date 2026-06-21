@echo off
setlocal

set CODEX_STARTED=0

for %%P in (
  "%LOCALAPPDATA%\Programs\Codex\Codex.exe"
  "%LOCALAPPDATA%\codex\Codex.exe"
  "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Codex.lnk"
  "%USERPROFILE%\Desktop\Codex.lnk"
) do (
  if exist %%~P (
    start "" %%~P
    set CODEX_STARTED=1
    goto :done
  )
)

where codex >nul 2>nul
if %ERRORLEVEL%==0 (
  start "Codex CLI" cmd /k "cd /d C:\XAU_ELITE_AI && codex"
  set CODEX_STARTED=1
  goto :done
)

:done
if "%CODEX_STARTED%"=="0" (
  echo Codex nao foi encontrado automaticamente.
  echo Abra o Codex manualmente uma vez e me informe o caminho do atalho se quiser fixar.
)

exit /b 0
