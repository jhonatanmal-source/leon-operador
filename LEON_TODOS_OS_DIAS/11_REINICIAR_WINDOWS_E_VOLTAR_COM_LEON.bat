@echo off
setlocal

echo Este script vai reiniciar o Windows.
echo Antes de continuar, garanta que o script 09 ja foi executado.
echo Assim o LEON volta automaticamente apos login.
echo.
choice /C SN /M "Deseja reiniciar agora"

if errorlevel 2 (
  echo Reinicio cancelado.
  pause
  exit /b 0
)

shutdown /r /t 15 /c "Reiniciando para liberar memoria e voltar com LEON XAU AI."
