# RELATÓRIO DE DESEMPENHO — SHADOW TRADES

- **Missão**: MISSION-20260805-DESEMPENHO
- **Classificação**: DESEMPENHO / OPERACIONAL LEON
- **Data**: 2026-08-05
- **Diretor**: LEON Engineering Director
- **Método**: Análise somente-leitura de `data/shadow_trades.csv` + dados de candles + código `src/shadow_trade.py` / `src/smc_price_levels.py`
- **Status**: ✅ DIAGNÓSTICO CONCLUÍDO — RELATÓRIO PARA APROVAÇÃO

---

## 1. RESUMO EXECUTIVO

| Métrica | Valor | Avaliação |
|---------|-------|-----------|
| Operações registradas | 55 | — |
| Fechadas (limpas) | 53 | excluído SHADOW-000041 (dado contaminado) |
| Wins | 14 | — |
| Losses | 39 | — |
| **Winrate** | **26.4%** | 🔴 abaixo do mínimo sustentável (~40% p/ RR 2) |
| Payoff acumulado | **-11R** | 🔴 negativo |
| Expectativa por trade | **-0.21R** | 🔴 negativo |
| Maior streak de losses | **7** | 🔴 risco (limite de pausa é 5) |
| RR técnico médio | 1.97 (fabricado) | ⚠️ ver seção 4 |

---

## 2. DIAGNÓSTICO DE DESEMPENHO POR DIMENSÃO

### 2.1 Por killzone (hora de entrada)

> **Nota metodológica**: Todas as tabelas desta seção usam o **conjunto limpo** (53 fechados, excluído SHADOW-000041 corrompido), corrigido após revisão.

| Janela | Trades | W/L | Winrate |
|--------|--------|-----|---------|
| Asia (00-05h) | 17 | 4W/13L | 23.5% 🔴 |
| **London (06-11h)** | **12** | **5W/7L** | **41.7% ✅ melhor** |
| NY (12-16h) | 13 | 4W/9L | 30.8% |
| **Late (17-23h)** | **11** | **1W/10L** | **9.1% 🔴 pior** |

**Achado**: Entradas na janela Late (17-23h) têm winrate de 9.1% — matematicamente inviável mesmo com RR 2 (breakeven = 33.3%). London (06-11h) é o único horário com winrate acima do breakeven. ⚠️ Amostra pequena (n=11 em Late, n=12 em London) — ver LIMITAÇÕES.

### 2.2 Por direção

| Direção | Trades | Winrate |
|---------|--------|---------|
| COMPRA | 28 | 28.6% |
| VENDA | 25 | 24.0% |

Leve vantagem em COMPRA, mas ambos abaixo do breakeven.

### 2.3 Por dia da semana

| Dia | Trades | Winrate |
|-----|--------|---------|
| Monday | 6 | 0.0% 🔴 |
| Tuesday | 13 | 23.1% |
| Wednesday | 11 | 27.3% |
| Thursday | 14 | 35.7% ✅ |
| Friday | 9 | 33.3% |

**Achado**: Monday = 0 wins em 6 trades. Amostra pequena, mas consistente com baixa liquidez/início de semana.

### 2.4 Por qualidade de entrada (missing_confirmations)

| Missing | Trades | Winrate |
|---------|--------|---------|
| 1 (mais forte) | 4 | 50.0% ✅ |
| 2 (moderada) | 8 | 25.0% |
| 3 (fraca) | 37 | 24.3% 🔴 |
| 4 (fraca) | 4 | 25.0% 🔴 |

**Achado**: Quanto menos confirmações faltando, maior o winrate. **70% dos trades (37/53) entram com 3 confirmações faltando (entrada FRACA)** — viola a preferência operacional de "confirmação estrutural completa". ⚠️ Células com n pequeno (missing=1: n=4, missing=2: n=8) — ver LIMITAÇÕES.

### 2.5 Componentes de confirmação

| Componente | Presente em | Winrate |
|------------|-------------|---------|
| FIBONACCI_ONDA_2_OU_4 | 44 | 23% 🔴 |
| CAPTURA_LIQUIDEZ | 42 | 29% |
| TOP_DOWN_H4_H1_M15 | 42 | 24% 🔴 |
| SMC_CHOCH_BOS | 19 | 26% |

**Achado**: Nenhum componente individual garante winrate; o que mais degrada é o combo `FIBONACCI_ONDA_2_OU_4` + `TOP_DOWN_H4_H1_M15` (24x, winrate 25%).

### 2.6 Evolução temporal (correções C1-C8)

| Janela | Trades | Winrate | Payoff |
|--------|--------|---------|--------|
| Pré-correções (22-27/07) | 19 | 26.3% | -4R |
| Pós C1-C8 (28-31/07) | 25 | 24.0% | -7R |
| Semana atual (03-05/08) | 9 | 33.3% | +0R |

**Achado**: As correções C1-C8 não melhoraram o winrate — pioraram levemente no período imediato. A semana atual mostra recuperação, mas com amostra pequena (9 trades) e 3 wins no período (000051, 000053, 000054 — **não consecutivos**, há LOSS 000052 entre eles).

---

## 3. CAUSA RAIZ CRÍTICA — TP TÉCNICO NÃO APLICADO

### 3.1 Evidência

- **54 de 55 trades (98%) têm RR exatamente 2.00**
- Único caso com RR técnico real: SHADOW-000045 (RR 0.38, target técnico próximo — **e ainda assim venceu**)
- Teste em 128 janelas de dados reais: `build_smc_trade_levels` retorna `None` em **99% dos casos**

### 3.2 Cadeia causal no código

```
src/smc_price_levels.py build_smc_trade_levels():
  → retorna None quando: sem FVG, preço fora da zona FVG, sem swings, sem alvo RR>=1
  → em 99% dos casos de teste → None

src/shadow_trade.py register_shadow_trade():
  → target = levels["tp2"] if levels.get("tp2") else entry + risk * 2
  → levels é None → FALLBACK: entry + risk * 2 → fabrica RR 2.0
```

### 3.3 Qualificação da causa (revisão Trading Systems Engineer) ⚠️ IMPORTANTE

- O teste original (128 janelas) usou `data/candle_history.csv`, que contém **snapshots de tick** (múltiplas linhas/min com OHLC repetido), NÃO candles M15 consolidados.
- **Com candles M15 reais** (como o MT5 entrega em produção): FVG detectado em **~78%** das janelas (não 8-12%); `build_smc_trade_levels` ainda retorna None em ~92%, mas o motivo dominante muda para **"preço atual fora da zona FVG" (~70%)**, não FVG ausente.
- Adicionalmente: quando `entry_price` é fornecido, a checagem `zone_low <= current_price <= zone_high` usa `candles[-1]["close"]` em vez do `entry` — inconsistência que rejeita ~72% dos FVG válidos.
- **Conclusão**: a causa raiz (fallback `risk*2` fabrica RR 2.00) está **CONFIRMADA na essência**. O motivo mais preciso é "FVG existe, mas preço/entrada raramente dentro da zona na hora do cálculo" + "falta alvo swing pagando >=1R". A correção prioritária não é relaxar FVG, e sim corrigir a cadeia.

### 3.4 Impacto

1. **TP técnico (regra operacional: "TP técnico") NÃO está sendo usado** em 98% dos shadow trades
2. O SL usa zona (C4), mas o TP cai sempre para `risk * 2` — viola a regra "RR deve ser calculado após TP e SL técnicos"
3. O resultado WIN_2R é sempre target=2R, independente de existir resistência/suporte estrutural entre entry e target
4. A métrica de payoff em R (2R/win) superestima o que um TP técnico real pagaria (ex: 000045 pagaria apenas 0.38R se usado TP técnico, não 2R)
5. **Divergência de política**: `entry_price_engine.py` BLOQUEIA a entrada quando não há níveis técnicos ("SEM ENTRADA: preco fora do FVG ou alvo tecnico..."); o shadow trade, com o mesmo None, fabrica RR e entra. Políticas divergentes para a mesma função.

---

## 4. ANOMALIA DE DADOS

| Item | Detalhe |
|------|---------|
| SHADOW-000041 | entry=2301.8 no Gold_Spot (~4100), event_signature `T1|T2` atípica, stop=2299.5, target=2306.4 — **feed corrompido**, WIN registrado por engano |
| Impacto | Se não excluído: winrate sobe falsamente para 27.8% e payoff -9R |

**Recomendação**: Adicionar guard de sanidade de preço (ex: |entry - preço atual| < 30%) para rejeitar entries anômalas no registro de shadow trade.

---

## 5. RECOMENDAÇÕES (PARA DECISÃO DO USUÁRIO)

### Prioridade alta
1. **Corrigir a cadeia do TP técnico**: eliminar o fallback `entry ± risk*2` em `register_shadow_trade` (retornar `NO_TECHNICAL_TP` quando `levels` é None, com paridade ao `entry_price_engine`). Corrigir a referência de preço na checagem de zona (usar `entry`, não `candles[-1]["close"]`). Usar swings S/R da mesma estrutura que define o SL como target. **Não relaxar o FVG** (em produção com M15 o FVG existe em ~78% — o gargalo real é a checagem de zona). **Sem isso, todo resultado é enviesado**.
2. **Bloquear/restringir janela Late (17-23h)**: winrate 9.1% em 11 trades. ⚠️ Amostra pequena (IC 95% ~0-40%) — recomendação para monitoramento estendido + decisão do usuário, não auto-execução.

### Prioridade média
3. **Exigir entradas mais fortes**: 70% dos trades têm 3 confirmações faltando. Considerar gate mínimo (max 2 missing) para liberar shadow trade. ⚠️ Evidência fraca (n=4-8 nas células de referência) — monitorar antes de endurecer.
4. **Guard de sanidade de preço** contra feeds corrompidos (caso 000041): rejeitar |entry - preço atual| anômalo no registro.
5. **Rotular resultado pelo RR técnico real** (não fixo WIN_2R): `evaluate_shadow_trades` grava sempre "WIN_2R" mesmo quando TP técnico é 0.38R — a régua de payoff deve refletir o RR real registrado.
6. **Unificar FVG**: duas implementações inconsistentes (`detect_latest_fvg` vs `_latest_fvg_near_event`) fragmentam o contrato operacional.

### Observação
7. **Monday (0/6)**: monitorar, amostra pequena.
8. **Telegram desabilitado** (`LEON_TELEGRAM_ENABLED=false`) — pendência de credenciais, não relacionada ao desempenho mas afeta observabilidade.

---

## 6. LIMITAÇÕES DA ANÁLISE

- **Amostras pequenas**: janela Late (n=11), Monday (n=6), missing=1 (n=4), missing=2 (n=8). Conclusões sobre esses grupos são indicativas, não estatisticamente conclusivas.
- **Fuso horário das horas de entrada**: as horas (killzones) usam o fuso local do servidor; a conversão exata para UTC/London pode deslocar fronteiras das killzones.
- **Teste de falha do TP**: o teste de 128 janelas usou `data/candle_history.csv` (snapshots de tick, não candles M15 consolidados). A qualificação com M15 real foi feita pelo Trading Systems Engineer por agregação manual — recomendado revalidar com candles M15 nativos do MT5.
- **Métrica de payoff em R**: assume RR fixo 2R/win, 1R/loss — não reflete o TP técnico real (98% fabricado), superestimando ganhos.
- **SHADOW-000041 excluído**: tabelas desta revisão usam conjunto limpo (53); a inclusão do dado corrompido alteraria winrate para 27.8% e payoff -9R (falso).

---

## 7. EVIDÊNCIAS E MÉTODO

- Fonte primária: `data/shadow_trades.csv` (55 registros completos com SL/TP/confirmações)
- Validação: script Python reproduzível em `/tmp/opencode/analise_desempenho.py`, `analise_temporal.py`, `analise_padroes.py`, `verifica_rr.py`
- Código revisado: `src/shadow_trade.py` (L57-128), `src/smc_price_levels.py` (L80-145), `src/entry_price_engine.py` (comparação de política)
- Teste de falha: 128 janelas em `data/candle_history.csv` (9667 registros) + agregação M15 pelo Trading Systems Engineer
- Revisão independente: Trading Systems Engineer (validação causa raiz) + Engineering Reviewer (validação numérica, veredito: APROVADO COM RESSALVAS)
- Nenhuma alteração de código feita — missão somente leitura

---

## 8. CHECKPOINT

- [x] TRIAGEM
- [x] DIAGNÓSTICO (dados coletados, métricas calculadas, causa raiz confirmada)
- [x] PLANO (perguntas definidas)
- [x] IMPLEMENTAÇÃO (análise executada)
- [x] REVISÃO (Trading Systems Engineer + Engineering Reviewer)
- [x] SEGURANÇA (não aplicável — sem alterações de código)
- [x] DOCUMENTAÇÃO (relatório + aprendizado diário registrado)
- [x] RELATÓRIO (este documento)
- [ ] APROVAÇÃO DO USUÁRIO
