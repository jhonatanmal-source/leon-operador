@echo off
cd /d C:\XAU_ELITE_AI
powershell -NoProfile -ExecutionPolicy Bypass -File ATALHOS_LEON\scripts\iniciar_leon_diario.ps1
timeout /t 2 /nobreak >nul
if exist data\link_painel_web.txt (
    powershell -NoProfile -Command "$u=(Get-Content -LiteralPath 'data\link_painel_web.txt' -Raw).Trim([char]0xFEFF).Trim(); if($u -match '^https://'){Start-Process $u}else{Start-Process 'http://DESKTOP-S6RGAFI:5000/login'}"
) else (
    start "" "http://DESKTOP-S6RGAFI:5000/login"
)
