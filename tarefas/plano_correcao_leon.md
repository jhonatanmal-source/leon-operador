# Plano de Correção — LEON XAU ELITE AI

## Prioridades

| ID | Sev | Descrição | Arquivo | Esforço |
|----|-----|-----------|---------|---------|
| A01 | P1 | Implementar ou remover `openrouter_client.py` | `src/openrouter_client.py` | 30 min |
| A02 | P1 | Implementar lógica real em `live_operational_contract.py` | `src/live_operational_contract.py` | 30 min |
| A03 | P1 | Implementar lógica real em `performance_engine.py` | `src/performance_engine.py` | 30 min |
| B03 | P2 | Corrigir 3 testes que não coletam (criar ou remover módulos) | `tests/` | 1h |
| B04 | P2 | Escrever testes para módulos críticos (mt5_order_executor, leon.py, risk_control_agent) | `tests/` | 5h |
| C01 | P3 | Mover `teste_*.py` de `src/` para `tests/` ou remover | `src/teste_*.py` | 15 min |
| C02 | P3 | Resolver import `telegram_config` — tornar arquivo local ou ajustar path | `telegram_engine.py` | 15 min |

---

## Dependências

```
A01 (isolado)
A02 (isolado)
A03 (isolado)
B03 -> depende de criar módulos src.backtest, contextual_memory, src.live_causal_confirmation
B04 -> isolado
C01 (isolado)
C02 (isolado)
```

## Ordem Sugerida

1. A01, A02, A03 (P1 — paralelizável)
2. C02 (P3 — import quebrado)
3. B04 (P2 — cobertura crítica)
4. B03 (P2 — testes quebrados)
5. C01 (P3 — limpeza)
