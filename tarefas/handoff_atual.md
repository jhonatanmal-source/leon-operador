# Handoff Atual

## 🎯 Última Missão Concluída: MISSION-20260817-BASE-DIAS-CORRIDOS
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
6. **Gap de dados 12-17/08** — 197 operações fechadas perdidas no incidente; avaliar se backups externos em `/opt/leon/leon_2026*.tar.gz` permitem recuperação (missão separada)
7. **Dívida técnica**: `_consecutive_losses()` ainda por contagem; consumidores `performance_engine`, `risk_method_engine`, `telegram_commands_mcp`, `daily_learning_report` calculam winrate sem janela
8. **`tests/test_leon_brain.py`** usa `sys.exit(0)` no módulo — suíte exige `--ignore` (dívida conhecida)
9. **Backup externo dos CSVs de `data/`** — nenhum backup completo dos CSVs operacionais (`shadow_trades.csv`, `pre_operation_trades.csv`, `operation_decisions.csv`); backups disponíveis vão só até 05/08. Tornou o gap 12-17/08 irreversível. Missão de infraestrutura dedicada (ex.: agendar `tar.gz` de `data/` + rotacionar no próprio host e/ou remoto). Aprendizado registrado em 2026-08-17.
10. **🔴 CRÍTICA — Correção do gatilho de entrada + guard de posição SMC**: LEON está **comprando topo e vendendo fundo** (winrate VENDA-FUNDO = 17.6%, COMPRA-TOPO = 41%; mediana posição: COMPRA 0.67 / VENDA 0.23 do range 48h). Causa raiz: gatilho M5 de ROMPIMENTO (`mt5_execution_refiner._micro_trigger`), zona = FVG de deslocamento (não demanda/oferta), sem guard de posição da entrada vs estrutura em nenhuma camada, `create_lab_zone` fabrica zonas CONFIRMADA. Recomendação do Trading Systems Engineer: **NÃO liberar execução (nem demo) baseada na evidência shadow atual** até corrigir 5.1 (gatilho de reteste) + 5.2 (guard de posição hard block). Missão dedicada com plano pronto (ver `tarefas/missoes/`). Aprendizado registrado em 2026-08-17.

## 🟢 Status Geral do Sistema
- **373/373** testes passando (com `--ignore=tests/test_leon_brain.py`)
- **Operator**: PID 3991171 ativo (`leon_operator.py`), ONLINE, autonomia demo ATIVA (scope `demo_execution`), conta real bloqueada
- **CSV pre_operation**: repopulando após incidente (PREOP-003478+)
- **MT5**: read-only via wine/rpyc
- **MCPs**: backtest, market, memory, replay registrados