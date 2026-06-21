@echo off
title LEON OPERATOR 24H

cd /d C:\XAU_ELITE_AI

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

python -B src\leon_operator.py --grant-autonomy-minutes 1440
python -B src\leon_operator.py

pause
