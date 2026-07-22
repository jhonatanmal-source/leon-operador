# Inventário de Revisão — LEON XAU ELITE AI

**Data:** 2026-07-20 14:30 UTC

---

## Módulos de Produção (`src/`)

### Análise Técnica
| Arquivo | Status | Observação |
|---------|--------|------------|
| `src/analysis/__init__.py` | ✅ OK | Único `__init__.py` no projeto |
| `src/analysis/choch_engine.py` | ✅ OK | Change of Character |
| `src/analysis/confirmation_engine.py` | ✅ OK | Confirmação estrutural |
| `src/analysis/context_engine.py` | ✅ OK | Contexto de mercado |
| `src/analysis/direction_engine.py` | ✅ OK | Direção |
| `src/analysis/fvg_engine.py` | ✅ OK | Fair Value Gap |
| `src/analysis/liquidity_engine.py` | ✅ OK | Liquidez |
| `src/analysis/setup_score.py` | ✅ OK | Pontuação de setup |
| `src/analysis/timing_engine.py` | ✅ OK | Timing |
| `src/analysis/volatility_engine.py` | ✅ OK | Volatilidade |
| `src/analysis/weekly_bias.py` | ✅ OK | Viés semanal |

### Núcleo Operacional
| Arquivo | Status | Observação |
|---------|--------|------------|
| `src/leon.py` | ✅ OK | Orquestrador principal |
| `src/leon_operator.py` | ⚠️ P1 | Parâmetro `nova_analise` não usado |
| `src/leon_config.py` | ✅ OK | Configurações globais |
| `src/leon_panel.py` | ✅ OK | Painel local |
| `src/pre_operation_engine.py` | ✅ OK | Pré-operação funcional |
| `src/mt5_order_executor.py` | ✅ OK | Execução MT5 com verificação de resultado |
| `src/mt5_engine.py` | ✅ OK | Engine MT5 |
| `src/mt5_connector.py` | ⚠️ P2 | Possível duplicata de `mt5_engine.py` |
| `src/log_engine.py` | ✅ OK | Logging de agentes |
| `src/operator_council.py` | ✅ OK | Conselho operador |

### Risco e Proteção
| Arquivo | Status | Observação |
|---------|--------|------------|
| `src/risk_control_agent.py` | ✅ OK | Agente de controle de risco |
| `src/capital_protection.py` | ✅ OK | Proteção de capital |
| `src/risk_manager.py` | ✅ OK | Gerenciador de risco |
| `src/discipline_guard.py` | ✅ OK | Guarda de disciplina |

### Análise de Mercado
| Arquivo | Status | Observação |
|---------|--------|------------|
| `src/market_reader.py` | ✅ OK | Leitor de mercado |
| `src/market_monitor.py` | ✅ OK | Monitor de mercado |
| `src/market_brain.py` | ✅ OK | Cérebro de mercado |
| `src/market_context_agent.py` | ✅ OK | Agente de contexto |
| `src/market_session_guard.py` | ✅ OK | Guarda de sessão |
| `src/market_score.py` | ✅ OK | Score de mercado |
| `src/market_memory.py` | ✅ OK | Memória de mercado |
| `src/market_story.py` | ✅ OK | Narrativa de mercado |

### SMC / Elliott / Fibonacci
| Arquivo | Status | Observação |
|---------|--------|------------|
| `src/smc_engine.py` | ✅ OK | Smart Money Concepts |
| `src/smc_study_engine.py` | ✅ OK | Estudo SMC |
| `src/smc_entry_guard.py` | ✅ OK | Guarda de entrada SMC |
| `src/smc_price_levels.py` | ✅ OK | Níveis de preço SMC |
| `src/elliott_engine.py` | ✅ OK | Ondas de Elliott |
| `src/elliott_study_engine.py` | ✅ OK | Estudo Elliott |
| `src/bos_engine.py` | ✅ OK | Break of Structure |
| `src/choch_engine.py` | ✅ OK | Change of Character |
| `src/choch_engine_v2.py` | ✅ OK | ChoCH v2 |
| `src/fvg_engine_v2.py` | ✅ OK | FVG v2 |
| `src/liquidity_engine_v2.py` | ✅ OK | Liquidez v2 |
| `src/interest_zone_engine.py` | ✅ OK | Zonas de interesse |
| `src/swing_engine.py` | ✅ OK | Swings |

### Stubs e Módulos Problemáticos
| Arquivo | Status | Problema |
|---------|--------|----------|
| `src/openrouter_client.py` | ❌ Stub | Arquivo vazio (0 linhas) |
| `src/live_operational_contract.py` | ❌ Stub | Sempre retorna `allowed=True` |
| `src/teste_mt5.py` | ⚠️ P3 | Arquivo de teste solto em src/ |
| `src/teste_telegram.py` | ⚠️ P3 | Arquivo de teste solto em src/ |
| `src/teste_mt5_telegram.py` | ⚠️ P3 | Arquivo de teste solto em src/ |
| `src/teste_institutional_analysis.py` | ⚠️ P3 | Arquivo de teste solto em src/ |
| `src/teste_fibonacci_wave_setup.py` | ⚠️ P3 | Arquivo de teste solto em src/ |
| `src/teste_material_elliott.py` | ⚠️ P3 | Arquivo de teste solto em src/ |
| `src/teste_bos.py` | ⚠️ P3 | Arquivo de teste solto em src/ |

### Outros Módulos
| Arquivo | Status |
|---------|--------|
| `src/brain_engine.py` | ✅ OK |
| `src/brain_analyzer.py` | ✅ OK |
| `src/brain_evolution.py` | ✅ OK |
| `src/brain_context_memory.py` | ✅ OK |
| `src/decision_engine.py` | ✅ OK |
| `src/data_engine.py` | ✅ OK |
| `src/candle_engine.py` | ✅ OK |
| `src/candle_reader.py` | ✅ OK |
| `src/entry_engine.py` | ✅ OK |
| `src/signal_engine.py` | ✅ OK |
| `src/signal_quality.py` | ✅ OK |
| `src/signal_logger.py` | ✅ OK |
| `src/signal_stats.py` | ✅ OK |
| `src/telegram_engine.py` | ✅ OK |
| `src/telegram_alert.py` | ✅ OK |
| `src/trade_judge.py` | ✅ OK |
| `src/trade_memory.py` | ✅ OK |
| `src/trade_explanation_engine.py` | ✅ OK |
| `src/timeframe_policy.py` | ✅ OK |
| `src/session_engine.py` | ✅ OK |
| `src/trend_reader.py` | ✅ OK |
| `src/trend_memory.py` | ✅ OK |
| `src/momentum_reader.py` | ✅ OK |
| `src/emotion_engine.py` | ✅ OK |
| `src/emotion_filter.py` | ✅ OK |
| `src/patience_engine.py` | ✅ OK |
| `src/autonomy_guard.py` | ✅ OK |
| `src/health_check.py` | ✅ OK |
| `src/performance_engine.py` | ✅ OK |
| `src/stats_engine.py` | ✅ OK |
| `src/price_logger.py` | ✅ OK |
| `src/error_logger.py` | ✅ OK |
| `src/journal_engine.py` | ✅ OK |
| `src/debug_engine.py` | ✅ OK |
| `src/memory_analyzer.py` | ✅ OK |
| `src/memory_rank.py` | ✅ OK |
| `src/learning_report.py` | ✅ OK |
| `src/daily_report.py` | ✅ OK |
| `src/daily_learning_report.py` | ✅ OK |
| `src/final_report.py` | ✅ OK |
| `src/night_learning.py` | ✅ OK |
| `src/night_collector.py` | ✅ OK |
| `src/collector_operator.py` | ✅ OK |
| `src/shadow_trade.py` | ✅ OK |
| `src/shadow_analysis.py` | ✅ OK |
| `src/operator_status.py` | ✅ OK |
| `src/operation_readiness.py` | ✅ OK |
| `src/operator_reputation_engine.py` | ✅ OK |
| `src/mt5_operation_close_monitor.py` | ✅ OK |
| `src/mt5_window_snapshot.py` | ✅ OK |
| `src/boot_counter.py` | ✅ OK |
| `src/screenshot_engine.py` | ✅ OK |
| `src/top_down_agent.py` | ✅ OK |
| `src/risk_method_engine.py` | ✅ OK |
| `src/hourly_analyzer.py` | ✅ OK |
| `src/repair_learning_memory.py` | ✅ OK |
| `src/price_logger.py` | ✅ OK |
| `src/lab_entry_policy.py` | ✅ OK |

---

## Testes

| Arquivo | Status | Testes |
|---------|--------|--------|
| `tests/test_agent_coordination.py` | ✅ OK | 24 |
| `tests/test_pre_operation_pipeline_consistency.py` | ✅ OK | 2 |
| `tests/test_interest_zone_engine.py` | ✅ OK | — |
| `tests/test_lab_entry_policy.py` | ✅ OK | — |
| `tests/test_leon_operator_resilience.py` | ✅ OK | — |
| `tests/test_market_session_guard.py` | ✅ OK | — |
| `tests/test_risk_context.py` | ✅ OK | — |
| `tests/test_telegram_retry.py` | ✅ OK | — |
| `tests/test_timeframe_policy.py` | ✅ OK | — |
| `tests/test_web_active_errors.py` | ✅ OK | — |
| `tests/test_weekly_audit_service.py` | ✅ OK | — |
| `tests/test_contextual_backtest_replayer.py` | ❌ Falha coleta | — |
| `tests/test_contextual_memory_integration.py` | ❌ Falha coleta | — |
| `tests/test_live_causal_operator.py` | ❌ Falha coleta | — |

---

## Painel Web

| Arquivo | Status |
|---------|--------|
| `web_app/app.py` | ✅ OK |
| `web_app/config.py` | ✅ OK |
| `web_app/__init__.py` | ✅ OK |
| `web_app/routes/auth_routes.py` | ✅ OK |
| `web_app/routes/leon_routes.py` | ✅ OK |
| `web_app/routes/health_routes.py` | ✅ OK |
| `web_app/routes/analysis_routes.py` | ✅ OK |
| `web_app/routes/dashboard_routes.py` | ✅ OK |
| `web_app/routes/user_routes.py` | ✅ OK |
| `web_app/routes/weekly_audit_routes.py` | ✅ OK |
| `web_app/services/auth_service.py` | ✅ OK |
| `web_app/services/web_security_service.py` | ✅ OK |
| `web_app/services/access_log_service.py` | ✅ OK |
| `web_app/services/upload_service.py` | ✅ OK |
| `web_app/services/system_health_service.py` | ✅ OK |
| `web_app/services/weekly_audit_service.py` | ✅ OK |
| `web_app/services/leon_understanding_service.py` | ✅ OK |
| `web_app/database/db.py` | ✅ OK |
| `web_app/templates/*` (11) | ✅ OK |
| `web_app/static/css/style.css` | ✅ OK |

---

## Configuração e Infraestrutura

| Item | Status |
|------|--------|
| `/opt/leon/config/.env` | 600 ✅ |
| `/opt/leon/app/.env` (symlink) | 777 (link) ✅ (segurança do alvo) |
| Crontab rpyc | ✅ @reboot |
| Wine Python 3.12.3 | ✅ |
| MetaTrader5 wheel 5.0.5735 | ✅ |
| rpyc 6.0.2 | ✅ |
| mt5linux_compat.py | ✅ |
| Dependências web | ✅ |
