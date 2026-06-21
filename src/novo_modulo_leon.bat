@echo off

set /p nome=Digite o nome do modulo:

type nul > C:\XAU_ELITE_AI\src\%nome%.py

echo.
echo Modulo criado:
echo %nome%.py
echo.

pause