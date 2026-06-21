@echo off
title LEON XAU AI - STATUS TELEGRAM

cd /d C:\XAU_ELITE_AI

python -B src\leon_operator.py --send-status --force

echo Status enviado para o Telegram.
pause
