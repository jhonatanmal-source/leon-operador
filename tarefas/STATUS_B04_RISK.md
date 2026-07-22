# STATUS B04 — CORREÇÃO risk_control_agent

**Status:** APROVADO

---

## 0. Estrutura

- **B04-01:** Correção de 3 falhas históricas (limite diário)
- **B04-02:** Normalização conservadora do lote com `math.floor` + `volume_step`

---

## 1. Causa de cada uma das três falhas (B04-01)

### Falha 1: `test_stop_zero` — `limite_percentual=0.0`

- **Teste esperava:** `approved=True`
- **Produção retornava:** `approved=False` (porque `0 > -0` é `False`)
- **Causa raiz:** A função `calcular_limite_perda_diaria` não validava `limite_percentual <= 0`. Um limite de 0% ou negativo não faz sentido como percentual de perda diária.
- **Decisão:** PRODUÇÃO INCORRETA (falta de validação). Adicionada validação que retorna `INVALID_LOSS_LIMIT`.

### Falha 2: `test_stop_negativo` — `limite_percentual=-1.0`

- **Teste esperava:** `approved=True`
- **Produção retornava:** `approved=False` (porque `0 > -(-100)` é `0 > 100` é `False`)
- **Causa raiz:** Mesma que a falha 1 — `limite_percentual <= 0` não era validado.
- **Decisão:** PRODUÇÃO INCORRETA. Corrigida pela mesma validação `INVALID_LOSS_LIMIT`.

### Falha 3: `test_resultado_nao_finito` — `saldo_atual=inf`

- **Teste esperava:** `ok=False`, `error="INVALID_STARTING_BALANCE"`
- **Produção retornava:** `ok=True` (porque `inf <= 0` é `False`)
- **Causa raiz:** A função não validava finitude dos parâmetros numéricos.
- **Decisão:** PRODUÇÃO INCORRETA. Adicionada validação `math.isfinite(saldo_atual)` antes do cálculo. O teste estava correto.

## 2. Contrato correto de stop

`calcular_plano_risco` recebe preços absolutos de entrada e stop. A distância é calculada como `abs(entrada - stop)`. Zero e negativo como distância são sempre rejeitados com `INVALID_STOP_DISTANCE`. Stop acima da entrada é válido para venda; stop abaixo é válido para compra — a direção não é validada nesta função (é responsabilidade de `smc_entry_guard`).

`calcular_limite_perda_diaria` recebe `limite_percentual` como percentual — zero ou negativo são rejeitados.

## 3. Contrato correto de números finitos

`math.isfinite(valor)` é aplicado antes de qualquer cálculo relevante. Valores `nan`, `inf`, `-inf` nos parâmetros críticos (saldo, resultado, entrada, stop, risco_percentual) retornam erro explícito com `ok=False`.

## 4. Decisão produção versus teste

| Teste | Decisão | Ação |
|-------|---------|------|
| `test_stop_zero` → `test_limite_zero_rejeitado` | PRODUÇÃO INCORRETA | Adicionada validação `limite_percentual <= 0` → `INVALID_LOSS_LIMIT` |
| `test_stop_negativo` → `test_limite_negativo_rejeitado` | PRODUÇÃO INCORRETA | Mesma validação |
| `test_resultado_nao_finito` → `test_saldo_infinito_rejeitado` | PRODUÇÃO INCORRETA | Adicionada validação `math.isfinite()` |

Os 3 testes existentes foram substituídos por testes com asserções corretas e nomes representativos.

## 5. Arquivos modificados

| Arquivo | B04-01 | B04-02 |
|---------|--------|--------|
| `src/risk_control_agent.py` | Validações de finitude (`math.isfinite`), `limite_percentual <= 0`, `CONTRACT_SIZE_XAU <= 0`, `saldo <= 0`, `risco_percentual` inválido, `distancia_stop` não finita, bloqueio de lote mínimo que excede risco máximo | Novas funções `_validar_especificacoes()`, `_normalizar_lote()`; `calcular_plano_risco` aceita parâmetro `especificacoes` opcional; normalização usa `math.floor(lote_bruto / volume_step + epsilon) * volume_step` em vez de `round(..., 2)`; risco efetivo recalculado pós-normalização |
| `tests/test_risk_control_agent.py` | Reescrevido com 33 testes em 2 classes | Expandido para 49 testes (15 limite diário + 34 plano risco) com 18 itens da especificação B04-02 Fase 5 |
| `src/mt5_order_executor.py` | — | Guard `INVALID_LOT` para lote ≤ 0 (linha ~903) |
| `tests/test_mt5_order_executor.py` | — | 2 novos testes (`test_lote_invalido_bloqueado`, `test_lote_negativo_bloqueado`) |

## 6. Testes criados/corrigidos

### TestLimitePerdaDiaria (15 testes)

| Teste | O que verifica |
|-------|----------------|
| `test_risco_normal` | Perda dentro do limite → aprovado |
| `test_limite_diario_atingido` | Perda acima do limite → bloqueado |
| `test_saldo_invalido` | Saldo total zero → `INVALID_STARTING_BALANCE` |
| `test_saldo_negativo` | Saldo inicial negativo → bloqueado |
| `test_lucro_nao_bloqueia` | Lucro não bloqueia execução |
| `test_limite_zero_rejeitado` | `limite_percentual=0` → `INVALID_LOSS_LIMIT` |
| `test_limite_negativo_rejeitado` | `limite_percentual=-1` → `INVALID_LOSS_LIMIT` |
| `test_saldo_infinito_rejeitado` | `saldo_atual=inf` → `INVALID_STARTING_BALANCE` |
| `test_saldo_nan_rejeitado` | `saldo_atual=nan` → `INVALID_STARTING_BALANCE` |
| `test_saldo_neg_infinito_rejeitado` | `saldo_atual=-inf` → `INVALID_STARTING_BALANCE` |
| `test_resultado_realizado_nao_finito_rejeitado` | Resultado realizado nan → `INVALID_RESULT` |
| `test_resultado_aberto_nao_finito_rejeitado` | Resultado aberto inf → `INVALID_RESULT` |
| `test_exposicao_existente_considerada` | Exposição existente reduz margem |
| `test_saldo_muito_grande` | Valor extremo não quebra |
| `test_perda_zero_com_limite_positivo` | Perda zero com limite positivo → aprovado |

### TestPlanoRisco (34 testes — B04-01 original + B04-02 novos)

#### B04-01 — Validações básicas (16 testes)

| Teste | O que verifica |
|-------|----------------|
| `test_plano_valido` | Setup básico com saldo → ok |
| `test_stop_zero_rejeitado` | `stop == entrada` → `INVALID_STOP_DISTANCE` |
| `test_stop_acima_entrada_eh_valido_para_venda` | Stop > entrada é válido (venda) |
| `test_stop_valido_compra` | Stop < entrada é válido (compra) |
| `test_stop_valido_venda` | Stop > entrada é válido (venda) |
| `test_entrada_igual_stop_rejeitado` | Distância zero → rejeitado |
| `test_saldo_zero_rejeitado` | `saldo=0` → `INVALID_BALANCE` |
| `test_saldo_negativo_rejeitado` | `saldo=-500` → `INVALID_BALANCE` |
| `test_saldo_infinito_rejeitado` | `saldo=inf` → `INVALID_BALANCE` |
| `test_saldo_nan_rejeitado` | `saldo=nan` → `INVALID_BALANCE` |
| `test_entrada_nan_rejeitada` | `entrada=nan` → `INVALID_PRE_OPERATION_PRICE` |
| `test_stop_nan_rejeitado` | `stop=nan` → `INVALID_PRE_OPERATION_PRICE` |
| `test_sem_entrada_rejeitado` | Chave ausente → `INVALID_PRE_OPERATION_PRICE` |
| `test_sem_stop_rejeitado` | Chave ausente → `INVALID_PRE_OPERATION_PRICE` |
| `test_lote_abaixo_minimo_bloqueia_quando_excede_risco` | Lote calculado < min_lot e min_lot excede risco → bloqueado |
| `test_sem_chamada_real_mt5` | Nenhuma chamada MT5 no cálculo com saldo fornecido |
| `test_sem_order_send` | Resultado não contém `order_send` |
| `test_contrato_ok_approved_mantem_campos_essenciais` | Resultado aprovado contém `lot`, `stop_distance`, `risk_value` |

#### B04-02 — Normalização conservadora (18 testes — Fase 5 da especificação)

| # | Teste | O que verifica |
|---|-------|----------------|
| 1 | `test_item1_lote_016_step_01_resultado_01` | lote_bruto=0.016, step=0.01 → lot=0.01 (nunca 0.02) |
| 2 | `test_item2_lote_019_step_01_resultado_01` | lote_bruto=0.019, step=0.01 → lot=0.01 |
| 3 | `test_item3_lote_020_step_01_resultado_02` | lote_bruto=0.020, step=0.01 → lot=0.02 |
| 4 | `test_item4_normalizacao_step01` | `_normalizar_lote(0.26, 0.1)` = 0.2 |
| 5 | `test_item5_normalizacao_step10` | `_normalizar_lote(1.9, 1.0)` = 1.0 |
| 6 | `test_volume_step_zero_rejeitado` | volume_step=0 → `INVALID_VOLUME_STEP` |
| 7 | `test_volume_step_negativo_rejeitado` | volume_step=-0.01 → `INVALID_VOLUME_STEP` |
| 8 | `test_volume_step_nan_rejeitado` | volume_step=NaN → `INVALID_VOLUME_STEP` |
| 9 | `test_volume_min_maior_que_max_rejeitado` | volume_min > volume_max → `INVALID_VOLUME_LIMITS` |
| 10 | `test_lote_minimo_dentro_risco_permitido` | min_lot respeita risco máximo → permitido |
| 11 | `test_lote_minimo_excedendo_risco_bloqueado` | min_lot excede risco máximo → `LOT_BELOW_MINIMUM_EXCEEDS_RISK` |
| 12 | `test_lote_maximo_aplicado_risco_recalculado` | max_lot aplicado, risco efetivo recalculado |
| 13 | `test_item13_lote_nunca_maior_que_calculado_exceto_min_lot` | lote final ≤ lote calculado quando > min_lot |
| 14 | `test_risco_efetivo_apos_normalizacao_nao_excede_maximo` | risco efetivo pós-normalização ≤ max_risk_percent |
| 15 | `test_precisao_decimal_estavel` | lote não contém artefatos `999999`/`000001` |
| 16 | `test_sem_chamada_real_mt5` | nenhuma chamada real MT5 |
| 17 | `test_sem_order_send` | resultado não contém `order_send` |
| 18 | `test_lote_com_especificacoes_personalizadas` | especificações injetadas são propagadas corretamente |

## 7. Baseline antes

```
166 passed, 3 failed (test_stop_zero, test_stop_negativo, test_resultado_nao_finito)
```

## 8. Resultado final

```
193 passed, 0 failed  (B04-01)
211 passed, 0 failed  (B04-02 — full suite)
```

### Detalhamento B04-02

```
test_risk_control_agent.py  — 49 passed
  TestLimitePerdaDiaria     — 15 passed
  TestPlanoRisco            — 34 passed
test_mt5_order_executor.py — 12 passed (2 novos: lote_invalido, lote_negativo)
tests/ total                — 211 passed
```

Nova cobertura de especificações do símbolo:
- `contract_size` — validado (`> 0`, finito)
- `volume_step` — validado (`> 0`, finito)
- `volume_min` — validado (`> 0`, finito, ≤ volume_max)
- `volume_max` — validado (`> 0`, finito, ≥ volume_min)
- `tick_size` — validado (opcional, `> 0`, finito)
- `tick_value` — validado (opcional, `> 0`, finito)

## 9. Casos de stop para compra e venda

- **Compra:** entrada na parte inferior, stop abaixo. Ex: entrada=2000, stop=1990 → distância=10. ✅ Aceito.
- **Venda:** entrada na parte superior, stop acima. Ex: entrada=2000, stop=2010 → distância=10. ✅ Aceito.
- **Stop inválido:** entrada=stop=2000 → distância=0 → `INVALID_STOP_DISTANCE`. ❌ Rejeitado.
- **Stop não finito:** `stop=nan` ou `stop=inf` → `INVALID_PRE_OPERATION_PRICE`. ❌ Rejeitado.

A função não valida direção (BUY/SELL) — isso é responsabilidade dos guards de SMC.

## 10. Casos NaN e infinito

Cobertos para:
- `saldo_atual` (`calcular_limite_perda_diaria`): `nan`, `inf`, `-inf` → `INVALID_STARTING_BALANCE`
- `resultado_realizado`: `nan`, `inf`, `-inf` → `INVALID_RESULT`
- `resultado_aberto`: `nan`, `inf`, `-inf` → `INVALID_RESULT`
- `saldo` (`calcular_plano_risco`): `nan`, `inf` → `INVALID_BALANCE`
- `entrada`: `nan` → `INVALID_PRE_OPERATION_PRICE`
- `stop`: `nan` → `INVALID_PRE_OPERATION_PRICE`
- `distancia_stop`: se `entrada - stop` resultar em não finito → `INVALID_STOP_DISTANCE`
- `risco_percentual`: se `metodo["risk_percent"]` ou `config["max_risk_percent"]` for não finito ou ≤ 0 → `INVALID_RISK_PERCENT`

## 11. Algoritmo de normalização do lote (B04-02)

### Problema corrigido

A versão anterior usava `round(lote_calculado, 2)`, que NÃO é conservador:

```python
round(0.016, 2) == 0.02  # ❌ arredondou para cima!
```

Isso poderia fazer o lote final exceder o risco máximo permitido.

### Algoritmo atual

```python
def _normalizar_lote(lote_bruto, volume_step):
    steps = int(math.floor(lote_bruto / volume_step + 1e-12))
    return round(steps * volume_step, 12)
```

- `1e-12` (epsilon) evita que `1.9999999` vire 1 step em vez de 2
- `round(..., 12)` elimina artefatos de ponto flutuante (ex: `1.000000000001`)
- O resultado sempre satisfaz `lote_normalizado <= lote_bruto` (piso matemático)

### Fluxo completo

1. `lote_bruto = risco_valor / (distancia_stop * contract_size)`
2. `lote_normalizado = _normalizar_lote(lote_bruto, volume_step)`
3. Se `lote_normalizado` é `None` (negativo/não finito) → `INVALID_CALCULATED_LOT`
4. Se `lote_normalizado < volume_min`:
   - Calcula risco real de `volume_min`
   - Se `risco_efetivo_percent > max_risk_percent` → `LOT_BELOW_MINIMUM_EXCEEDS_RISK`
   - Senão, usa `volume_min`
5. Se `lote_normalizado > volume_max` → cap para `volume_max`
6. Recalcula `risco_efetivo = lote * distancia_stop * contract_size`
7. Recalcula `risco_efetivo_percent = (risco_efetivo / saldo) * 100`
8. Aprova somente se `risco_efetivo_percent <= max_risk_percent`

### Exemplos manuais

| Entrada | Stop | Distância | Saldo | Risco% | Lote bruto | Volume step | Lote normalizado | Risco efetivo% |
|---------|------|-----------|-------|--------|------------|-------------|-----------------|----------------|
| 2000.0 | 1900.0 | 100.0 | 10.000 | 0,5% | 0,005 | 0,01 | 0,01 (min_lot) | 1,00% |
| 2000.0 | 1900.0 | 100.0 | 32.000 | 0,5% | 0,016 | 0,01 | 0,01 | 0,50% |
| 2000.0 | 1900.0 | 100.0 | 40.000 | 0,5% | 0,020 | 0,01 | 0,02 | 0,50% |
| 2000.0 | 1900.0 | 100.0 | 100.000 | 0,5% | 0,050 | 0,01 | 0,05 | 0,50% |

### Fonte do volume_step

- `volume_step` vem do parâmetro `especificacoes` (opcional)
- Default seguro: `0.01` (padrão XAUUSD)
- Pode ser injetado pelo pipeline a partir das especificações do símbolo MT5
- Nenhuma conexão real MT5 ocorre nos testes

### Validação fail-closed de especificações

`_validar_especificacoes(esp)` bloqueia quando:
- `contract_size` ausente, zero, negativo, não finito
- `volume_step` ausente, zero, negativo, não finito
- `volume_min` ou `volume_max` inválidos, ou `min > max`
- `tick_size` ou `tick_value` inválidos (quando fornecidos)

Códigos de erro: `INVALID_CONTRACT_SIZE`, `INVALID_VOLUME_STEP`, `INVALID_VOLUME_LIMITS`, `INVALID_TICK_SPECIFICATION`, `INVALID_CALCULATED_LOT`.

## 12. Evidência de fail-closed

### Risk control agent

`calcular_plano_risco` retorna `ok=False` com erro explícito para qualquer entrada inválida:
- Preço ausente/não finito → `INVALID_PRE_OPERATION_PRICE`
- Stop inválido → `INVALID_STOP_DISTANCE`
- Especificações inválidas → `INVALID_VOLUME_STEP`, `INVALID_CONTRACT_SIZE`, etc.
- Lote calculado inválido → `INVALID_CALCULATED_LOT`
- Lote mínimo excede risco → `LOT_BELOW_MINIMUM_EXCEEDS_RISK`

### Executor (mt5_order_executor.py)

```python
# Guard diário (linha ~579)
limite_diario = avaliar_limite_perda_diaria()
if not limite_diario.get("ok"):
    return _bloqueio("DAILY_LOSS_GUARD_UNAVAILABLE", ...)
if not limite_diario.get("approved"):
    return _bloqueio("DAILY_LOSS_LIMIT_REACHED", ...)

# Guard de risco (linha ~869)
plano_risco = calcular_plano_risco(...)
if not plano_risco.get("approved"):
    return _bloqueio("RISK_CONTROL_BLOCKED", ...)

# Guard de lote inválido (linha ~903, adicionado B04-02)
if lote <= 0:
    return _bloqueio("INVALID_LOT", ...)

# Guard de lote máximo (linha ~908)
if lote > config["lot"]:
    return _bloqueio("LOT_ABOVE_EXECUTION_LIMIT", ...)
```

Toda falha de risco ou lote inválido → retorno de bloqueio explícito → nenhuma execução.

## 13. Evidência de que order_send não foi chamado

- `calcular_limite_perda_diaria` e `calcular_plano_risco` não fazem `order_send`.
- Testes `test_sem_order_send` e `test_sem_chamada_real_mt5` confirmam.
- `mt5_order_executor.py` só chama `order_send` após todos os guards passarem (linha ~950+).

## 14. Evidência de que conta REAL permanece bloqueada

`mt5_order_executor.py` possui guard `ACCOUNT_TRADE_MODE_DEMO` + `MT5_REAL_ACCOUNT_BLOCKED` antes de qualquer chamada de risco. O módulo `risk_control_agent.py` não tem acesso a `order_send` e não pode liberar execução.

`_validar_especificacoes` e `_normalizar_lote` em `risk_control_agent.py` são funções puras — não fazem conexão MT5, não consultam conta real, não enviam ordens.

## 15. Regressões encontradas

Nenhuma.

```
B04-01: 193 passed, 0 failed
B04-02: 211 passed, 0 failed (+18 novos testes, +2 executor, +2 guards)
```

## 16. Pendências

Nenhuma. B04-01 e B04-2 concluídos.

## 17. Contrato size e ticks (Fase 6)

A fórmula atual `distancia_stop * contract_size` é suficiente para XAUUSD:
- `contract_size = 100` (padrão XAUUSD)
- `tick_size` e `tick_value` são aceitos como opcionais em `_validar_especificacoes`
- Para XAUUSD no MT5 Demo brasileiro, a fórmula canônica `distancia_stop * contract_size` produz o valor monetário correto do risco
- `tick_size * tick_value` não é necessário para este par pois o contrato é diretamente em USD
- Se no futuro um símbolo diferente exigir a fórmula canônica, `especificacoes` permite injetar `tick_size` e `tick_value` sem quebrar compatibilidade
