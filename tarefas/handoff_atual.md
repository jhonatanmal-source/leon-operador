# Handoff Atual

## 🎯 Última Missão Concluída: MISSION-20260818-BACKUP-RESGATE-DADOS
- **Fase 2 do plano de execução** (pendências #6 e #9)
- **Status**: ✅ CONCLUÍDA
- **Backup automático dos CSVs operacionais**: `scripts/backup_operational_data.sh` (backup/status/verify), snapshot leve 1.5M, checksum sha256, rotação 48, agendado no crontab do `leon` (`0 * * * *`)
- **Resgate do gap 12-17/08**: gap ERA recuperável (pendência #6 estava incorreta). Backup `leon_20260817_031822.tar.gz` (03:18, anterior ao incidente das 21:03) preservou a janela. Merge não-destrutivo aplicado: 73 → **297 pre-ops** (224 recuperadas, 103 fechadas com resultado). Swap atômico, perm/owner preservados.
- **Incidente secundário corrigido**: `logs/operator_out.log` era `root:leon` (640) → restart automático do operador estava quebrado. Log removido, operador reiniciado (**PID 3395248**).
- **Testes**: 373 passed (`--ignore=tests/test_leon_brain.py`)
- **Rollback**: snapshot `opdata_20260818_053146.tar.gz` guarda a versão pré-swap (74 linhas)
- **Doc**: `tarefas/missoes/MISSION-20260818-BACKUP-RESGATE-DADOS.md`

## Missão Anterior: MISSION-20260817-BASE-DIAS-CORRIDOS
- **Base de desempenho trocada de contagem para janela de dias corridos** (`[BASELINE] window_days = 30`)
- **Status**: ✅ APROVADO (Architect: APROVADO COM AJUSTES; Reviewer: APROVADO COM RESSALVAS, corrigidas)
- **Testes**: 373 passed, 0 falhas (`--ignore=tests/test_leon_brain.py`)
- **Arquivos**: `src/baseline_window.py` (novo), `tests/test_baseline_window.py` (novo, 17 testes), `pre_operation_engine.py`, `learning_bootstrap.py`, `operation_readiness.py`, `lab_entry_policy.py`, `operation_batch_review.py`, `leon_panel.py`, `test_performance_engine.py`, `config.ini` + `config.ini.example`

## 🚨 Incidente Tratado (severidade ALTA)
- `tests/test_performance_engine.py` truncou `data/pre_operation_trades.csv` real (370 linhas → header) em 17/08 21:03 ao rodar a suíte
- **Causa raiz**: teste escrevia/apagava no `data/` real (sem tmp_path) — landmine pré-existente
- **Correção**: fixture autouse `_isolar_csv(tmp_path, monkeypatch)`; validado CSV intacto (md5 idêntico antes/depois)
- **Recuperação**: NÃO recuperável integralmente (197 operações fechadas 12-17/08 perdidas; nenhum CSV residual tem resultado/data_fechamento; backups até 05/08)
- **Integridade**: sequence_file preservou numeração (novo = PREOP-003478, sem colisão)
- **Operador**: ONLINE, autonomia ATIVA, CSV repopulando

## 📁 Arquivos Modificados (missão)
| Arquivo | Mudança |
|---------|---------|
| `src/baseline_window.py` | NOVO — helper de janela (obter_window_days, parse_datetime, dentro_da_janela) |
| `tests/test_baseline_window.py` | NOVO — 17 testes |
| `src/pre_operation_engine.py` | `resumo_pre_operacao(window_days=None)`; `ultimo/total/abertos` globais |
| `src/learning_bootstrap.py` | `_winrate_shadows_recentes(window_days)` |
| `src/operation_readiness.py` | passa `obter_window_days()`; expõe `window_days` em rules |
| `src/lab_entry_policy.py` | `shadow_evidence(window_days)`; janela só na produção |
| `src/operation_batch_review.py` | janela + dedup por `operation_ids` + seed migração |
| `src/leon_panel.py` | novas chaves do state batch_learning |
| `tests/test_performance_engine.py` | isolamento tmp_path (correção incidente) |
| `config.ini` + `config.ini.example` | seção `[BASELINE] window_days = 30` |

## 📋 Pendências Pós-Missão
1. **Rotacionar senha do usuário `jhonatan`** (dashboard web) — comprometida em 30/07
2. **Telegram desabilitado** — `LEON_TELEGRAM_ENABLED=false` (token comprometido)
3. **Backtest MCP** — ainda simulação estrutural (`candles_analyzed: 0`)
4. **Persistir razão do bloqueio de auto-simulate** (achado C5) — hoje só vai ao stdout
5. **Renovar autorização demo semanalmente** — operador NÃO renova automaticamente quando `AUTONOMY_EXPIRED`
6. ~~**Gap de dados 12-17/08**~~ ✅ RESOLVIDO (MISSION-20260818): gap ERA recuperável. 224 pre-ops recuperadas do backup `leon_20260817_031822.tar.gz`. Restante: fatia PREOP-003330→003477 (17/08 03:18→21:03) só existe em 67 `.txt` — sub-tarefa opcional (parser dos .txt), tratar depois.
7. **Dívida técnica**: `_consecutive_losses()` ainda por contagem; consumidores `performance_engine`, `risk_method_engine`, `telegram_commands_mcp`, `daily_learning_report` calculam winrate sem janela
8. **`tests/test_leon_brain.py`** usa `sys.exit(0)` no módulo — suíte exige `--ignore` (dívida conhecida)
9. ~~**Backup externo dos CSVs de `data/`**~~ ✅ RESOLVIDO (MISSION-20260818): `scripts/backup_operational_data.sh` implantado (snapshot 1.5M somente-leitura, sha256, rotação 48) e agendado no crontab do `leon` (`0 * * * *`). Log em `/opt/leon/logs/backup_operational_data.log`. Validado em `env -i`.
11. **Restart automático do operador era falha silenciosa** (descoberto em 2026-08-18): `logs/operator_out.log` pertencia a `root:leon` (640) e o `start-operator.sh`, rodando como `leon`, falhava com `Permission denied` — o operador não voltaria sozinho se caísse. Log removido e operador reiniciado. **Pendente**: impedir recorrência (evitar que processo root crie logs do operador; considerar `logrotate` com `su leon leon` ou criar o log com owner correto no script).
10. ~~**🔴 CRÍTICA — Correção do gatilho de entrada + guard de posição SMC**~~ ✅ IMPLEMENTADO (MISSION-20260818-CORRECAO-ENTRADA-SMC, aguardando commit): LEON estava **comprando topo e vendendo fundo** (winrate VENDA-FUNDO = 17.6%, COMPRA-TOPO = 41%; mediana posição: COMPRA 0.67 / VENDA 0.23 do range 48h). Correções aplicadas no escopo **A + C** (escolha do usuário): **A** — `_micro_trigger` reescrito: confirmação exige sweep de liquidez + reclaim + displacement e NUNCA rompimento de estrutura (anti perseguir preço); **C** — `create_lab_zone` não fabrica mais `CONFIRMADA` (nasce `AGUARDANDO_ESTRUTURA`, sem `structural_confirmations`/`valid_confirmations` fabricados) e SMC guard passou a ser **sempre ativo** (LAB_LEARNING não pula mais o guard). Guard de posição 3.2 (hard block) **NÃO implementado** — sem evidência nos dados recuperados. 387 testes passando. Reviewer: APROVADO COM RESSALVAS (corrigidas). **Impacto operacional**: execução demo LAB via bootstrap fica bloqueada até existir mecanismo de confirmação estrutural real (follow-up) — ver relatório da missão.

## 🟢 Status Geral do Sistema
- **387/387** testes passando (com `--ignore=tests/test_leon_brain.py`)
- **Operator**: PID **3395248** ativo (`leon_operator.py`), ONLINE, autonomia demo ATIVA (scope `demo_execution`), conta real bloqueada — reiniciado em 2026-08-18 após correção de permissão de log. ⚠️ O operador em execução ainda roda o código antigo até ser reiniciado (correção SMC entra no próximo restart — requer autorização).
- **CSV pre_operation**: 297 pre-ops (PREOP-003106→003550), gap 12-17/08 recuperado
- **Backup operacional**: horário via `scripts/backup_operational_data.sh` → `/opt/leon/backups/operational_data/` (rotação 48)
- **MT5**: read-only via wine/rpyc
- **MCPs**: backtest, market, memory, replay registrados
- ⚠️ **Alerta operacional ativo**: pendência #10 (compra topo/vende fundo) NÃO resolvida — operador segue enviando ordens demo VENDA em SETUP FRACO (ex.: PREOP-003504/003505 em 18/08). Priorizar Fase 1 (correção SMC).