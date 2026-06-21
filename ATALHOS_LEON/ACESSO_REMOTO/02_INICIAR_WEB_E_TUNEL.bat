@echo off
title LEON ACESSO REMOTO
cd /d C:\XAU_ELITE_AI
echo ========================================
echo LEON ACESSO REMOTO
echo ========================================
echo Iniciando painel e acesso HTTPS seguro...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File ATALHOS_LEON\scripts\iniciar_leon_diario.ps1

echo Painel disponivel no endereco fixo:
echo https://leon-operador.tailcdf4e1.ts.net/login
echo.
echo Nao e necessario abrir portas no modem.
echo Envie o link e as credenciais somente para operadores autorizados.
echo.
pause
