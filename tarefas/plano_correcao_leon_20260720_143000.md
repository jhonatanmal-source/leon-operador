# Plano de Correção — LEON XAU ELITE AI

**Data:** 2026-07-20 14:30 UTC
**Revisão:** Tarefa 4 — Diagnóstico Completo

---

## Prioridades

| ID | Severidade | Descrição | Arquivo | Esforço |
|----|-----------|-----------|---------|---------|
| FIX-01 | P1 | Remover parâmetro `nova_analise` não utilizado | `src/leon_operator.py:167` | 5 min |
| FIX-02 | P1 | Implementar `openrouter_client.py` ou remover importações | `src/openrouter_client.py` | 30 min |
| FIX-03 | P1 | Implementar `live_operational_contract.py` com lógica real | `src/live_operational_contract.py` | 30 min |
| FIX-04 | P2 | Adicionar `__init__.py` em `src/` e subdiretórios | `src/__init__.py`, etc. | 10 min |
| FIX-05 | P2 | Escrever testes para `mt5_order_executor.py` | `tests/` | 2h |
| FIX-06 | P2 | Escrever testes para `leon.py` | `tests/` | 2h |
| FIX-07 | P2 | Escrever testes para `risk_control_agent.py` | `tests/` | 1h |
| FIX-08 | P3 | Adicionar `__init__.py` em `tests/` | `tests/__init__.py` | 5 min |
| FIX-09 | P3 | Remover ou mover arquivos `teste_*.py` de `src/` | `src/teste_*.py` | 15 min |

---

## Detalhamento

### FIX-01: Parâmetro não usado em `_iniciar_identidade_ciclo`

**Arquivo:** `src/leon_operator.py:167-171`
**Problema:** A função aceita `nova_analise=False` mas nunca usa o parâmetro.
**Correção:** Remover o parâmetro e ajustar chamadores.
**Risco:** Nenhum — parâmetro já é ignorado.

### FIX-02: Stub `openrouter_client.py`

**Arquivo:** `src/openrouter_client.py`
**Problema:** Arquivo vazio (0 linhas). Qualquer import falha.
**Correção:** Implementar cliente OpenRouter com fallback ou remover todas as referências ao módulo.
**Risco:** Baixo — se ninguém importa, remover é seguro.

### FIX-03: Stub `live_operational_contract.py`

**Arquivo:** `src/live_operational_contract.py`
**Problema:** Sempre retorna `allowed=True` com reason `"LIVE_GATE_NOT_IMPLEMENTED"`.
**Correção:** Implementar lógica de confirmação real ou documentar que é um stub intencional.
**Risco:** Médio — se chamado em produção, permite qualquer operação.

### FIX-04: `__init__.py` faltantes

**Problema:** Nenhum diretório em `src/` (exceto `src/analysis/`) tem `__init__.py`. Imports relativos quebram.
**Correção:** Criar `__init__.py` em `src/`, `src/contract/` (se existir), etc.
**Risco:** Nenhum — pacotes Python padrão.

### FIX-05, 06, 07: Testes faltantes

**Problema:** 91% dos módulos sem teste, incluindo orquestrador principal e executor de ordens.
**Correção:** Escrever testes unitários com mocking do MT5.
**Risco:** Nenhum — apenas adiciona cobertura.

---

## Dependências entre correções

```
FIX-01 (isolado)
FIX-02 -> depende de saber quem importa openrouter_client
FIX-03 -> depende de especificação do live gate
FIX-04 -> (isolado)
FIX-05 -> FIX-04 (precisa de __init__.py para imports)
FIX-06 -> FIX-04
FIX-07 -> FIX-04
FIX-08 -> (isolado)
FIX-09 -> (isolado)
```

**Ordem sugerida:** FIX-04 → FIX-05/06/07 → FIX-01/02/03 → FIX-08/09
