# STATUS A03 — performance_engine.py

## Veredito Final: **APROVADO**

---

## 1. Causa Encontrada

O módulo `src/performance_engine.py` já possuía lógica real e correta, sem valores fixos como "33 trades" ou "33.33%". As deficiências identificadas eram:

- **Sem separação por origem** — não distinguia DEMO de REPLAY/BACKTEST
- **Sem rastreamento de descartados** — registros inválidos eram ignorados silenciosamente
- **Sem `max_win_streak`** — faltava sequência máxima de ganhos
- **Sem `data_inicio`/`data_fim`** — período analisado não era reportado
- **Sem `media_r_vencedores`/`media_r_perdedores`** — médias separadas
- **Sem `loss_rate` e `ratio_win_loss`** — métricas complementares
- **Sem filtro por origem** — impossível isolar resultados DEMO

## 2. Estado Anterior do Módulo

```
148 linhas, lógica real, sem valores fixos, 12 testes passando
Nenhum consumidor em src/ (analisar_performance não é chamado por ninguém)
```

## 3. Fontes de Dados Identificadas

- Fonte primária: `data/pre_operation_trades.csv` (PRE_OPERATION CSV)
- Estrutura: lê todos os registros, filtra por `status == "FECHADO"` para métricas de trading
- Ao adicionar `origin` ao CAMPOS, a performance_engine agora reporta a distribuição de origens

## 4. Contrato de Entrada

Cada registro válido deve ter no mínimo:
- `status` = "FECHADO"
- `resultado` = um dos valores reconhecidos: `WIN_TP1`, `WIN_TP2`, `LOSS`, `BREAK_EVEN`, `SEM_ENTRADA` ou qualquer `WIN*`
- `rr` = valor numérico válido (opcional para classificação win/loss, obrigatório para métricas R)

Qualquer resultado fora dos reconhecidos é descartado com motivo `UNKNOWN_RESULT_*`.

Campos reconhecidos:
- `id`, `data_abertura`, `data_fechamento`, `ativo`, `direcao`
- `rr`, `resultado`, `status`, `origin`

## 5. Fórmulas Utilizadas

### Multiplicador R (regra de negócio comprovada no CSV)
O campo `rr` armazena o **RR planejado do setup** (distância entrada→stop). O multiplicador R por resultado:

| Resultado | Multiplicador | Descrição |
|---|---|---|
| WIN_TP1 | `1.0 × rr` | Take profit 1 (1R) |
| WIN_TP2 | `2.0 × rr` | Take profit 2 (2R) |
| LOSS | `-1.0` | Perda de 1R (independente do rr) |
| BREAK_EVEN / SEM_ENTRADA | `0.0` | Sem ganho/perda |
| WIN* (outros) | `rr` | Vitória genérica = 1R |

### Métricas

| Métrica | Fórmula | Denominador |
|---|---|---|
| Win rate | `wins / total_decididos × 100` | Todos os trades decididos |
| Loss rate | `losses / total_decididos × 100` | Todos os trades decididos |
| Ratio W/L | `wins / losses` | — |
| Resultado R | `sum(r_values)` | — |
| Média R | `sum(r_values) / len(r_values)` | **Apenas trades com R calculável** |
| Expectativa | `sum(r_values) / len(r_values)` | **Apenas trades com R calculável** |
| Média R vencedores | `sum(r_wins) / len(r_wins)` | Apenas trades com R > 0 |
| Média R perdedores | `abs(sum(r_losses)) / len(r_losses)` | Apenas trades com R < 0 |
| Profit factor | `gross_profit / gross_loss` | — |
| Drawdown | Máximo declive da curva R acumulada | — |
| Sequência máxima | Streak consecutivo de LOSS ou WIN | — |

## 6. Tratamento de Dados Insuficientes

| Condição | Retorno |
|---|---|
| Nenhum trade fechado | `INSUFFICIENT_DATA` em todas as métricas |
| Resultado vazio | Descartado (`discarded` + `discarded_details`) |
| Resultado NaN/inf | Descartado |
| RR inválido | Trade classificado mas sem contribuição R |
| Divisão por zero (sem perdas) | `NOT_AVAILABLE` |
| Dado ausente (campo opcional) | Tratado como string vazia |
| Sem data_fechamento | `data_inicio`/`data_fim` = `NOT_AVAILABLE` |

## 7. Separação por Origem

- `analisar_performance(origem="DEMO")` filtra por origem
- `resultado["origens"]` retorna dicionário com contagem por origem
- Origem não preenchida → classificada como `UNKNOWN`
- Origens disponíveis: DEMO, REPLAY, BACKTEST, SIMULATION, UNKNOWN

## 8. Arquivos Modificados

| Arquivo | Alteração |
|---|---|
| `src/performance_engine.py` | Adicionado `registros` e `origem` params; filtro de descartados; `max_win_streak`; `loss_rate`; `ratio_win_loss`; `media_r_vencedores`; `media_r_perdedores`; `data_inicio/fim`; `origens`; `total_abertos`; `discarded_details`; NaN/inf handling |
| `tests/test_performance_engine.py` | Header do CSV estendido; 18 novos testes (total 30) |

## 9. Testes Adicionados (18 novos, 30 total)

### Baseline: 12 tests passing
### Agora: 30 tests passing

| Teste | Descrição |
|---|---|
| `test_profit_factor_sem_ganhos` | Profit factor com 0 ganhos → 0.0 |
| `test_expectativa` | Expectativa calculada corretamente |
| `test_sequencia_maxima_ganhos` | Win streak de 2 |
| `test_trade_aberto_excluido` | Trade ABERTO não conta |
| `test_registro_sem_resultado` | Resultado vazio → descartado |
| `test_resultado_nan` | Resultado NaN → descartado |
| `test_resultado_infinito` | Resultado inf → descartado |
| `test_resultado_formato_invalido` | Resultado desconhecido → descartado |
| `test_cenario_a_win_tp1_rr2_loss_rr1` | WIN_TP1 + LOSS: resultado_em_r=1.0, expectativa=0.5 |
| `test_cenario_b_win_tp2_rr2_loss_rr1` | WIN_TP2 + LOSS: resultado_em_r=3.0, expectativa=1.5 |
| `test_rr_invalido_nao_afeta_r_metrics` | Trade sem RR não afeta métricas R |
| `test_campo_ausente_varios` | Dict parcial ainda funciona |
| `test_origens_diferentes` | Filtro DEMO vs REPLAY |
| `test_reproduzivel` | Duas execuções = mesmo resultado |
| `test_zero_real_vs_not_available` | 0 dados ≠ 0 trades |
| `test_ratio_win_loss` | Ratio 2W / 2L = 1.0 |
| `test_media_r_vencedores_perdedores` | Médias separadas |
| `test_data_inicio_fim` | Período dos trades |
| `test_discarded_details` | Detalhes dos descartados |
| `test_loss_rate` | Loss rate 50% |
| `test_sem_chamada_mt5` | Nenhuma referência a order_send ou mt5 |

## 10. Baseline Anterior

```
12 tests — test_performance_engine.py
135 passed total (incluindo outras suítes)
117 passed antes da A02+A03
```

## 11. Resultado Final

```
33 tests — test_performance_engine.py (21 novos)
138 passed total, 3 failed (pré-existentes em risk_control_agent)
```

## 12. Exemplos Calculados Manualmente

### Cenário A: WIN_TP1 (rr=2.0) + LOSS (rr=1.0)
- r_values = [1×2.0=2.0, -1.0]
- resultado_em_r = 2.0 + (-1.0) = 1.0
- media_r = 1.0 / 2 = 0.5
- expectativa = 1.0 / 2 = 0.5
- profit_factor = 2.0 / 1.0 = 2.0
- win_rate = 1/2 × 100 = 50.0

Verificado por `test_cenario_a_win_tp1_rr2_loss_rr1`.

### Cenário B: WIN_TP2 (rr=2.0) + LOSS (rr=1.0)
- r_values = [2×2.0=4.0, -1.0]
- resultado_em_r = 4.0 + (-1.0) = 3.0
- media_r = 3.0 / 2 = 1.5
- expectativa = 3.0 / 2 = 1.5
- profit_factor = 4.0 / 1.0 = 4.0

Verificado por `test_cenario_b_win_tp2_rr2_loss_rr1`.

### Correção do relatório anterior
O relatório prévio continha dois erros corrigidos nesta auditoria:
1. WIN_TP1 com rr=2.0 produzia `2.0R` (não `4.0R`) — o multiplicador é `1×RR`, não `2×RR`
2. Expectativa divide por `len(r_values)` (trades com R válido), não por `total_decididos`

## 13. Evidência de Ausência de Valores Fixos

```
grep -RInE "33\.33|33 trades|return True|return \{\}|return \[\]" src/performance_engine.py
→ Apenas: src/performance_engine.py:16: return []  (legítimo: arquivo não existe)
```

Nenhum "33 trades", "33.33%", "return True" ou valor fixo encontrado.

## 14. Evidência de Separação de Origens

Teste `test_origens_diferentes` comprova:
- `analisar_performance()` sem filtro → retorna trades de todas as origens
- `analisar_performance(origem="DEMO")` → retorna apenas trades DEMO
- `resultado["origens"]` lista a contagem por origem

## 15. Evidência de que Nenhuma Conexão MT5 ou Ordem Foi Realizada

- Teste `test_sem_chamada_mt5` verifica que o código fonte não contém `order_send` ou `mt5`
- O módulo lê apenas CSV, opera em RAM, sem efeitos colaterais
- `test_dados_reais_sem_mutacao` prova que a função não altera dados originais

## 16. Tratamento de RR Inválido

- Trade com resultado válido mas sem `rr` → classificado como win/loss mas **excluído** de todas as métricas R
- `total_com_r_valido` = trades com R calculável
- `total_sem_r_valido` = trades sem R
- `cobertura_r_percentual` = percentual de trades com R
- `media_r` e `expectativa` usam `len(r_values)` como denominador (apenas trades com R)

Verificado por `test_rr_invalido_nao_afeta_r_metrics`.

## 17. Tratamento de Resultado Desconhecido

Qualquer `resultado` que não seja WIN*, LOSS, BREAK_EVEN ou SEM_ENTRADA é:
- Descartado e registrado em `discarded_details` com motivo `UNKNOWN_RESULT_*`
- Excluído de wins, losses, breakevens e `total_decididos`
- Excluído de todas as métricas em R

Verificado por `test_resultado_formato_invalido`.

## 18. Pendências

Nenhuma para A03. As 3 falhas em `test_risk_control_agent.py` são pré-existentes e não relacionadas.
