# MISSÃO: MISSION-20260817-BASE-DIAS-CORRIDOS

- **Data**: 2026-08-17
- **Classificação**: OPERACIONAL LEON / DADOS
- **Status**: ✅ CONCLUÍDA E APROVADA
- **Diretor**: LEON Engineering Director

## Resultado Final

Base de winrate do LEON trocada de **contagem de operações** para **janela de dias corridos** (`[BASELINE] window_days = 30`). Implementação validada: **373 testes passando, 0 falhas**. Software Architect: APROVADO COM AJUSTES. Engineering Reviewer: APROVADO COM RESSALVAS (2 ressalvas corrigidas).

### Incidente tratado durante a missão
Ao rodar a suíte, `tests/test_performance_engine.py` truncou o CSV operacional real (bug pré-existente de isolamento). **Corrigido** com fixture autouse `tmp_path` + `monkeypatch`. As 197 operações fechadas (12-17/08) não são recuperáveis integralmente — gap documentado, operador repopulando. Detalhes no checkpoint e nos aprendizados de 2026-08-17.

## Arquivos

| Arquivo | Mudança |
|---------|---------|
| `src/baseline_window.py` | NOVO — helper de janela (obter_window_days, parse_datetime, dentro_da_janela) |
| `tests/test_baseline_window.py` | NOVO — 17 testes (janela, parser, ultimo global, seed, dedup, timezone) |
| `src/pre_operation_engine.py` | `resumo_pre_operacao(window_days=None)`; `ultimo/total/abertos` globais |
| `src/learning_bootstrap.py` | `_winrate_shadows_recentes(window_days)`; auto_simulate passa janela |
| `src/operation_readiness.py` | passa `obter_window_days()`; expõe `window_days` em rules |
| `src/lab_entry_policy.py` | `shadow_evidence(window_days)`; janela só na produção |
| `src/operation_batch_review.py` | janela + dedup por `operation_ids` + seed migração de bloco_*.json |
| `src/leon_panel.py` | novas chaves do state batch_learning |
| `tests/test_performance_engine.py` | isolamento tmp_path (correção incidente) |
| `config.ini` + `config.ini.example` | seção `[BASELINE] window_days = 30` |

## Fases

| Fase | Status |
|------|--------|
| 1. TRIAGEM | COMPLETED |
| 2. DIAGNÓSTICO | COMPLETED |
| 3. PLANO | COMPLETED (APROVADO COM AJUSTES) |
| 4. CONVOCAÇÃO | COMPLETED |
| 5. IMPLEMENTAÇÃO | COMPLETED |
| 6. TESTES | COMPLETED (373 passed) |
| 7. REVISÃO | COMPLETED (APROVADO COM RESSALVAS, corrigidas) |
| 8. SEGURANÇA | COMPLETED (sem arquivos proibidos; conta real bloqueada) |
| 9. DOCUMENTAÇÃO | COMPLETED |
| 10. RELATÓRIO | COMPLETED |
| 11. APROVAÇÃO | ✅ APROVADO |

## Checkpoint

- Arquivo: `tarefas/checkpoint_base_dias_corridos_20260817.json`