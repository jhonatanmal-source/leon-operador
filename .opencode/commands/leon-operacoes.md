---
description: Mostrar status das operações — entradas de hoje, conta demo, sinais e conexão MT5.
---

Mostre o status operacional completo do LEON:

1. Verifique se o operador está rodando: `systemctl --user status leon-operator --no-pager -n 5`
2. Verifique o MT5: processo `terminal64.exe` rodando?
3. Leia `data/pre_operation_trades.csv` — quantas operações hoje?
4. Leia `data/trade_plan_memory.csv` — últimos planos gerados
5. Leia `data/signals.csv` — últimos sinais
6. Verifique `config.ini` — scope (demo_execution?)
7. Verifique quantas operações abertas (status=ABERTO no CSV)
8. Mostre winrate do dia se houver dados fechados

Apresente um resumo em formato de tabela:

| Indicador | Valor |
|-----------|-------|
| Operador | 🟢 Rodando / 🔴 Parado |
| MT5 | 🟢 Conectado / �️ Desconectado |
| Scope | demo_execution / learning |
| Operações hoje | N |
| Wins/Losses | X / Y |
| Winrate | Z% |
| Abertas | N |

Se não houver dados, informe claramente.
