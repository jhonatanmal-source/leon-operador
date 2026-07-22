# Simulação 4 — Replay Histórico

## Missão
Analise possíveis gargalos do replay histórico.

## Classificação
DESEMPENHO / DADOS

## Agentes escolhidos
- Engineering Director (coordenação)
- Performance Engineer (desempenho)
- Senior Software Engineer (análise técnica)
- Trading Systems Engineer (domínio)

## Arquivos analisados
- `tests/test_contextual_backtest_replayer.py` (8 testes, todos quebrados)
- `src/interest_zone_engine.py` (InterestZoneStore)
- Módulos esperados que não existem: `backtest/leon_strategy_replayer.py`, `backtest/statistical_report.py`, `context_decision.py`, `live_operational_contract.py`

## Problemas encontrados

### Crítico
1. **Módulos centrais do replay não existem** — `leon_strategy_replayer.py`, `statistical_report.py`, `backtest/` package, `context_decision.py`, `live_operational_contract.py` nunca foram criados.
2. **8 testes de replay 100% quebrados** — todos falham porque os módulos não existem.

### Alto
3. **Read-all/write-all** — `InterestZoneStore.upsert()` lê e escreve o dataset inteiro a cada operação. Sem indexação.
4. **Sem batch operations** — cada candle = 1 ciclo completo de I/O.
5. **JSON com `indent=2`** — 30-50% de overhead de tamanho.

### Médio
6. **O(n) linear scan** — `get()` e `upsert()` varrem todos os registros.
7. **Sem índice** — nenhum dict-index por `region_id`.
8. **Lock global serializa I/O** — `_STORE_LOCK` impede paralelismo.

## Conclusão
Sistema de replay não está funcionalmente implementado. O `InterestZoneStore` tem limitações de escala significativas. Recomenda-se SQLite ou JSON com journal.

## Nenhuma alteração funcional realizada
Modo somente leitura respeitado.
