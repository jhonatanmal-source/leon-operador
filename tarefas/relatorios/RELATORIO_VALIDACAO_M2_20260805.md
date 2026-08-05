# RELATÓRIO DE VALIDAÇÃO — IMPACTO M2 NA ENTRADA REAL

- **Missão**: MISSION-20260805-BACKTEST-M2
- **Classificação**: DESEMPENHO / OPERACIONAL LEON
- **Data**: 2026-08-05
- **Método**: Validação direta de `build_smc_trade_levels` com candles M15 nativos do MT5 (5000 candles reais)
- **Status**: ✅ VALIDAÇÃO CONCLUÍDA

---

## 1. LIMITAÇÃO DO BACKTEST MCP (descoberta importante)

O backtest via MCP (`src/mcp/leon_backtest_mcp.py`) é **apenas simulação estrutural**:
- Não chama `build_smc_trade_levels` nem `entry_price_engine`
- Usa análise SMA20 simplificada (`total_setups = len//10`)
- `candles_analyzed: 0` mesmo com MT5 disponível (bug de conversão numpy)
- Resultados BT-00001..00005 são **fictícios/estruturais** — não medem a estratégia

**Conclusão**: para medir o impacto real, a validação foi feita chamando o engine diretamente com dados reais.

---

## 2. RESULTADOS — COMPARAÇÃO ANTIGO vs NOVO (candles M15 reais)

**Amostra**: 5000 candles M15 Gold_Spot · 2470 janelas deslizantes (60 candles) × 2 direções = **4940 testes**

| Métrica | Código ANTIGO | Código NOVO (M1-M4) | Δ |
|---------|---------------|---------------------|---|
| Níveis OK | 333 (6.7%) | 83 (1.7%) | **-75%** |
| tp1 == tp2 colapsado | **168 (50.5% dos OK)** | 0 | eliminado pelo M2 |
| RR != 2.0 (TP técnico real) | — (sempre fabricava 2.0 no registro) | **82 de 83 (98.8%)** | ✅ |
| RR técnico médio | — | 3.63 | — |
| RR range | — | 1.06 – 7.90 (cap 8.0 ativo) | — |
| RR stdev | — | 1.88 | distribuição saudável |

---

## 3. INTERPRETAÇÃO DO IMPACTO M2

1. **Metade dos setups antigos era inválida**: 50.5% dos níveis OK no código antigo tinham `tp1 == tp2` colapsado — o M2 agora bloqueia esses (não há alvo de extensão real).
2. **Redução de ~75% dos setups elegíveis** (6.7% → 1.7%): a entrada real será mais seletiva. Isso é **intencional** — alinhado à regra "entrada somente em região válida" e "não entrar no meio do movimento".
3. **TP técnico autêntico em 98.8% dos novos casos**: a correção elimina a fabricação de RR 2.0.
4. **Risco residual**: volume menor de operações — monitorar se o sistema consegue capturar setups suficientes em períodos de maior liquidez (London 06-11h).

---

## 4. OBSERVAÇÃO TÉCNICA — BUG NO mt5_safe.py (✅ CORRIGIDO)

Durante a validação foi encontrado um bug separado: `mt5_safe.safe_copy_rates_from_pos` falha com `'numpy.void' object has no attribute 'time'` quando `copy_rates` retorna numpy ndarray.

**Causa raiz**: `copy_rates_from_pos` do `mt5linux_compat` retorna `numpy.ndarray` de `numpy.void` (campos acessíveis por chave `r["time"]`), mas a função wrapper acessava por atributo (`r.time`) — incompatível.

**Correção aplicada (MISSION-20260805-FIX-NUMPY)**:
- Helper `_field(row, name)`: tenta acesso por chave com fallback para atributo
- Conversão explícita para `float`/`int`
- `symbol_info_tick`/`symbol_info` verificados: NÃO têm o bug (retornam netref rpyc)

**Impacto pós-correção**:
- Backtest MCP agora obtém **1440 candles reais** (antes: 0)
- OHLC M15 (20 candles) retorna correto
- Símbolo inválido → dict de erro sem exceção
- 356 testes passando (zero regressão)
- Consumidores `candle_reader.py` (acesso por chave) e `mt5_candles.py` (pd.DataFrame) já funcionavam

**Status**: ✅ CORRIGIDO — pendente de commit (aguarda autorização do usuário)

---

## 5. RECOMENDAÇÕES

1. **Monitorar volume de operações** nas próximas 1-2 semanas — confirmar que a seletividade maior não para o aprendizado
2. ~~**Corrigir `safe_copy_rates_from_pos`** (conversão numpy)~~ → ✅ **CORRIGIDO** em 2026-08-05
3. **Melhorar o backtest MCP** para exercitar engines reais (agora possível — dados reais fluem; a simulação estrutural ainda é usada para setups)

---

## 6. CHECKPOINT

- [x] Backtest MCP executado (BT-00005) — revelou simulação estrutural
- [x] Validação direta com candles M15 reais (4940 testes)
- [x] Comparação antigo vs novo quantificada
- [x] Bug numpy em `safe_copy_rates_from_pos` corrigido (MISSION-20260805-FIX-NUMPY)
- [x] Aprendizado registrado + sync Obsidian
- [x] Relatório gerado
