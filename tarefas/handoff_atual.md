# Handoff Atual

## 🎯 Última Missão Concluída: Pendência #2 — Telegram REATIVADO (token real do BotFather)
- **Estado**: Telegram **ATIVO e operacional** — token real + chat_id configurados em `/opt/leon/app/.env` (`LEON_TELEGRAM_TOKEN`, `LEON_TELEGRAM_CHAT_ID=-1004376165028`, `LEON_TELEGRAM_ENABLED=true`); `config.ini` `[TELEGRAM] enabled = true`.
- **Validação em 3 camadas**: (1) `getMe` → `LeonXauEliteBot` válido; (2) `getChat` → supergrupo "LEON XAU AI - Estudos" válido; (3) envio real → `message_id 3364` entregue + log do operador `TELEGRAM | mensagem enviada com sucesso`.
- **Operador**: reiniciado (PID **3457923**) — processo vivo envia mensagens com sucesso.
- **⚠️ Decisão estrutural**: NÃO criar symlink `app/.env -> config/.env` — o `app/.env` tem chaves web reais (SECRET_KEY, admin) que não existem no `config/.env`; o placeholder antigo `COLAR_...` do `config/.env` seria lido como token. Fonte única efetiva: `/opt/leon/app/.env` + `config.ini`.
- **Arquivos**: `/opt/leon/app/.env` (credenciais, ignorado pelo git), `config.ini` (`enabled=true`, ignorado pelo git), `tarefas/aprendizados_diarios/CONTEXTO_EVOLUCAO.md`, `tarefas/aprendizados_diarios/2026-08-18.md`, `tarefas/handoff_atual.md` (este).
- **Sem commit** (aguardando autorização). Nenhuma alteração em MT5, risco, TP/SL ou execução.

## 🎯 Missão Anterior: Pendência #2 — Telegram alinhado DESABILITADO (config + doc)
- **Estado corrigido**: `config.ini` `[TELEGRAM] enabled = true` → `false` — runtime agora reporta `TELEGRAM_ENABLED = False` e `enviar_mensagem()` retorna `TELEGRAM_DISABLED` (antes: `enabled=true` sem token → `TELEGRAM_CONFIG_MISSING`, estado inconsistente com o handoff).
- **Causa da inconsistência**: `telegram_config.py` lê `ROOT_DIR/.env` (= `/opt/leon/app/.env`, arquivo real sem chaves Telegram) + `config.ini` como fallback. O `/opt/leon/config/.env` (com `LEON_TELEGRAM_ENABLED=false` + token placeholder `COLAR_...`) **NÃO é lido pelo runtime** — o symlink `app/.env -> config/.env` documentado em 22/07 foi sobrescrito em 27/07 por `.env` real (chaves web).
- **Risco documentado**: NÃO recriar o symlink enquanto o token em `/opt/leon/config/.env` for placeholder `COLAR_...` (seria lido como token configurado → POST inválido). Reativação exige token real do BotFather + `enabled = true` + teste de envio real.
- **Testes**: 39 telegram + suíte completa **398 passed** (`--ignore=tests/test_leon_brain.py`). Runtime validado: `TELEGRAM_ENABLED=False`, `TELEGRAM_DISABLED` no guard.
- **Arquivos**: `config.ini` (`enabled=false`), `tarefas/aprendizados_diarios/CONTEXTO_EVOLUCAO.md` (linha Telegram atualizada), `tarefas/aprendizados_diarios/2026-08-18.md` (aprendizado), `tarefas/handoff_atual.md` (este).
- **Sem commit** (aguardando autorização). Nenhuma alteração em código operacional, MT5, risco, TP/SL ou execução.

## 🎯 Missão Anterior: MISSION-20260818-FIX-MCP-MARKET (bug #12)
- **Bug corrigido**: `leon_market_mcp.py` importava `_MT5_AVAILABLE` por valor (cópia `False` no import) → todos os tools de mercado exceto `check_mt5_status` retornavam "MT5 não disponível" mesmo com MT5 saudável. Mesmo padrão em `leon_backtest_mcp.py`.
- **Correção**: helper `_mt5_disponivel()` → `check_mt5().get("available")` (dispara `_ensure_initialized()` real) nos 6 handlers do market MCP; backtest usa `check_mt5().get("available")` no lugar da flag estática.
- **Status**: ✅ IMPLEMENTADA + TESTADA + VALIDADA EM PRODUÇÃO (aguardando commit)
- **Testes**: 11 novos em `tests/test_market_mcp_availability.py`; suíte completa **398 passed** (`--ignore=tests/test_leon_brain.py`)
- **Validação em produção (MCP real via JSON-RPC)**: `get_account_info` → balance 10100.54, equity 10097.06, leverage 100 (antes: "MT5 não disponível"); `get_current_price Gold_Spot` → bid 4393.67/ask 4393.99; `get_ohlc` M15 real; `list_symbols` → Gold_Spot encontrado. Símbolo ativo da corretora: **Gold_Spot** (não XAUUSD).
- **Segurança**: nenhuma função de ordem exposta; somente leitura; conta real bloqueada.
- **Arquivos**: `src/mcp/leon_market_mcp.py`, `src/mcp/leon_backtest_mcp.py`, `tests/test_market_mcp_availability.py` (novo)

## 🎯 Missão Anterior: MISSION-20260818-CORRECAO-ENTRADA-SMC (encerramento pós-commit)
- **Commit `d1e6ba3`** (06:25:46) e **restart do operador às 06:27:01** — operador PID **3424309** JÁ roda o código novo (SMC guard sempre ativo em LAB_LEARNING; `_micro_trigger` com sweep+reclaim+displacement, sem perseguir estrutura).
- **Status**: ✅ IMPLEMENTADA + COMMITADA + VALIDADA (missão encerrada; ver MISSION-20260818-CORRECAO-ENTRADA-SMC.md)
- **Evidência em produção (Fase A)**: log 06:35+ mostra "SMC guard sempre ativo, timeframe_policy relaxado pelo laboratorio" (antes do restart: "SMC guard skipped"); PREOP-003551 em loop sem nova entrada — bloqueado por `MAX_OPEN_POSITIONS_REACHED` (2 abertas, limite 2), não mais pelo viés comprar topo/vender fundo.
- **Autonomia**: ativa (demo_execution) até 2026-08-18T20:32:24; heartbeat ONLINE (PID 3424309, `execution_authorized: true`); conta real bloqueada.
- **Achado novo (bug MCP, SEM correção nesta missão)**: `src/mcp/leon_market_mcp.py` importa `_MT5_AVAILABLE` **por valor** (cópia `False` no import) → todos os tools de mercado exceto `check_mt5_status` retornam "MT5 não disponível" mesmo com MT5 saudável (rpyc OK, porta 18812 aberta). A flag só é atualizada dentro de `mt5_safe`; os handlers não chamam `_ensure_initialized()`/`check_mt5()` antes. **Correção proposta**: handlers devem chamar `check_mt5()`/`_ensure_initialized()` antes de checar a flag, ou importar o módulo e ler `mt5_safe._MT5_AVAILABLE` dinamicamente. → Pendência nova #12.

## 🎯 Missão Anterior: MISSION-20260818-BACKUP-RESGATE-DADOS
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
2. **Telegram** — ✅ REATIVADO (2026-08-18): token real do BotFather + chat_id `-1004376165028` configurados em `/opt/leon/app/.env`; `config.ini` `enabled=true`; envio real validado (`message_id 3364`, grupo "LEON XAU AI - Estudos"). ⚠️ NÃO criar symlink `app/.env -> config/.env` (placeholder antigo `COLAR_...` no `config/.env` seria lido como token; `app/.env` tem chaves web reais).
3. **Backtest MCP** — ainda simulação estrutural (`candles_analyzed: 0`)
4. **Persistir razão do bloqueio de auto-simulate** (achado C5) — hoje só vai ao stdout
5. **Renovar autorização demo semanalmente** — operador NÃO renova automaticamente quando `AUTONOMY_EXPIRED`
6. ~~**Gap de dados 12-17/08**~~ ✅ RESOLVIDO (MISSION-20260818): gap ERA recuperável. 224 pre-ops recuperadas do backup `leon_20260817_031822.tar.gz`. Restante: fatia PREOP-003330→003477 (17/08 03:18→21:03) só existe em 67 `.txt` — sub-tarefa opcional (parser dos .txt), tratar depois.
7. **Dívida técnica**: `_consecutive_losses()` ainda por contagem; consumidores `performance_engine`, `risk_method_engine`, `telegram_commands_mcp`, `daily_learning_report` calculam winrate sem janela
8. **`tests/test_leon_brain.py`** usa `sys.exit(0)` no módulo — suíte exige `--ignore` (dívida conhecida)
9. ~~**Backup externo dos CSVs de `data/`**~~ ✅ RESOLVIDO (MISSION-20260818): `scripts/backup_operational_data.sh` implantado (snapshot 1.5M somente-leitura, sha256, rotação 48) e agendado no crontab do `leon` (`0 * * * *`). Log em `/opt/leon/logs/backup_operational_data.log`. Validado em `env -i`.
11. **Restart automático do operador era falha silenciosa** (descoberto em 2026-08-18): `logs/operator_out.log` pertencia a `root:leon` (640) e o `start-operator.sh`, rodando como `leon`, falhava com `Permission denied` — o operador não voltaria sozinho se caísse. Log removido e operador reiniciado. **Pendente**: impedir recorrência (evitar que processo root crie logs do operador; considerar `logrotate` com `su leon leon` ou criar o log com owner correto no script).
10. ~~**🔴 CRÍTICA — Correção do gatilho de entrada + guard de posição SMC**~~ ✅ IMPLEMENTADO + COMMITADO (MISSION-20260818-CORRECAO-ENTRADA-SMC, commit `d1e6ba3`): LEON estava **comprando topo e vendendo fundo** (winrate VENDA-FUNDO = 17.6%, COMPRA-TOPO = 41%; mediana posição: COMPRA 0.67 / VENDA 0.23 do range 48h). Correções aplicadas no escopo **A + C** (escolha do usuário): **A** — `_micro_trigger` reescrito: confirmação exige sweep de liquidez + reclaim + displacement e NUNCA rompimento de estrutura (anti perseguir preço); **C** — `create_lab_zone` não fabrica mais `CONFIRMADA` (nasce `AGUARDANDO_ESTRUTURA`, sem `structural_confirmations`/`valid_confirmations` fabricados) e SMC guard passou a ser **sempre ativo** (LAB_LEARNING não pula mais o guard). Guard de posição 3.2 (hard block) **NÃO implementado** — sem evidência nos dados recuperados. 387 testes passando. Reviewer: APROVADO COM RESSALVAS (corrigidas). **Impacto operacional**: execução demo LAB via bootstrap fica bloqueada até existir mecanismo de confirmação estrutural real (follow-up) — ver relatório da missão.
12. ~~**Bug MCP `_MT5_AVAILABLE` copiado por valor**~~ ✅ RESOLVIDO (MISSION-20260818-FIX-MCP-MARKET): `leon_market_mcp.py` importava a flag `False` por valor → `get_account_info`, `get_current_price`, `get_symbol_info`, `get_ohlc`, `list_symbols`, `get_market_snapshot` retornavam sempre "MT5 não disponível"; só `check_mt5_status` funcionava. Correção: helper `_mt5_disponivel()` → `check_mt5().get("available")` (dispara `_ensure_initialized()` real). Mesmo padrão corrigido em `leon_backtest_mcp.py`. Validado em produção (account info real, preço Gold_Spot real). 11 testes novos, 398 total.

## 🟢 Status Geral do Sistema
- **387/387** testes passando (com `--ignore=tests/test_leon_brain.py`)
- **Operator**: PID **3424309** ativo (`leon_operator.py`, reiniciado 2026-08-18 06:27:01), ONLINE, autonomia demo ATIVA (scope `demo_execution`, expira 18/08 20:32), conta real bloqueada. ✅ **RODA O CÓDIGO NOVO (commit `d1e6ba3`)** — SMC guard sempre ativo confirmado em produção (log 06:35+).
- **CSV pre_operation**: 297+ pre-ops (PREOP-003106→003558), gap 12-17/08 recuperado; 18 ABERTO, 137 FECHADO, 150 OBSERVADO
- **Backup operacional**: horário via `scripts/backup_operational_data.sh` → `/opt/leon/backups/operational_data/` (rotação 48)
- **MT5**: read-only via wine/rpyc (porta 18812 aberta, wineserver saudável)
- **MCPs**: backtest, market, memory, replay registrados — ✅ **market MCP funcional** (bug #12 corrigido: account info, preço Gold_Spot e OHLC reais)
- **Alerta operacional (pendência #10)**: ✅ RESOLVIDO — operador roda o guard SMC novo; entradas no quadrante comprar topo/vender fundo não passam mais