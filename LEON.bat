@echo off
title CENTRAL LEON
cd /d C:\XAU_ELITE_AI

:menu
cls
echo ========================================
echo           CENTRAL LEON
echo ========================================
echo.
echo 1 - Abrir painel web
echo 2 - Iniciar operador por 24 horas
echo 3 - Conceder autonomia por 2 horas
echo 4 - Configurar No-IP
echo 5 - Abrir pasta de atalhos
echo 6 - Iniciar HTTPS
echo 0 - Sair
echo.
set /p opcao=Escolha uma opcao: 

if "%opcao%"=="1" call "ATALHOS_LEON\USO_DIARIO\01_ABRIR_PAINEL_WEB.bat"
if "%opcao%"=="2" call "ATALHOS_LEON\USO_DIARIO\02_INICIAR_OPERADOR_24H.bat"
if "%opcao%"=="3" call "ATALHOS_LEON\USO_DIARIO\04_AUTONOMIA_2H.bat"
if "%opcao%"=="4" call "ATALHOS_LEON\ACESSO_REMOTO\01_ATIVAR_NOIP.bat"
if "%opcao%"=="5" start "" explorer "C:\XAU_ELITE_AI\ATALHOS_LEON"
if "%opcao%"=="6" call "ATALHOS_LEON\ACESSO_REMOTO\05_INICIAR_HTTPS.bat"
if "%opcao%"=="0" exit /b 0

goto menu
