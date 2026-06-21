@echo off
title LEON CLOUDFLARE TUNNEL
cd /d C:\XAU_ELITE_AI
echo ========================================
echo INICIANDO CLOUDFLARE TUNNEL - LEON
echo ========================================
echo Copie o link https://...trycloudflare.com
echo Envie somente para operadores autorizados.
echo ========================================

if exist tools\cloudflared.exe (
    tools\cloudflared.exe tunnel --url http://127.0.0.1:5000
) else (
    cloudflared tunnel --url http://127.0.0.1:5000
)

pause
