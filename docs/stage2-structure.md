# Etapa 2.1 — eventos estruturais causais

## Diagnóstico e plano

O inventário local encontrou `analisar_bos(df)` em `src/market_monitor.py:40`
e `src/teste_bos.py:22`. Ambos consultam MT5 a partir da posição 0 (candle
aberto) e usam o retorno como texto. CHOCH/FVG legados não têm chamadas de
produção encontradas; o MCP de backtest apenas importa seus módulos.

O caminho institucional usa `src/smc_engine.py` → `analyze_smc_context`.
O Grok sugeriu reutilizar esse caminho antes de substituir os módulos legados.
A revisão local encontrou um defeito prévio nele: a compressão global de
pivôs consecutivos permite que um extremo futuro apague um pivô anterior e,
consequentemente, um BOS histórico.

A fixture de `tests/test_causal_structure.py` reproduz: com 21 candles, aparece
BOS_BULLISH no índice 19, nível 104 e fechamento 105; com 30 candles, o código
anterior elimina esse evento. O último candle de cada entrada é considerado
aberto e excluído da análise.

## Correção

- `detect_structure_pivots` preserva todos os extremos confirmados e registra
  `confirmed_index = index + window`.
- `detect_structure_events` usa esses pivôs por padrão e só disponibiliza cada
  um após sua confirmação. O rompimento continua exigindo fechamento estrito.
- `analyze_smc_context` usa o fluxo causal para eventos. `detect_pivots` mantém
  a lista alternada e seu formato anterior para Elliott e viés do snapshot.
- Quem fornecer pivôs explicitamente deve fornecer uma lista não comprimida;
  para janelas diferentes de 2, deve incluir `confirmed_index`.

## Testes e revisão

22 testes passaram em Python 3.14: fixture de regressão, invariância de eventos
em todos os prefixos de 20 séries determinísticas, confirmação atrasada,
pavio versus fechamento, candle aberto, BOS/CHOCH, níveis não repetidos,
contrato de pivôs de Elliott e testes existentes de liquidez/Fibonacci.

O Grok participou do diagnóstico inicial, mas atingiu seu limite de uso antes
de revisar a descoberta de causalidade ou este patch. A afirmação inicial do
Grok de ausência de look-ahead não foi tomada como prova; foi confrontada com
o código e com a reprodução. Revisão do patch: Codex.

## Limitações e próximas etapas

Este patch altera a sequência BOS/CHOCH consumida pela análise institucional;
exige revisão de impacto e validação no ambiente Python 3.12 antes de deploy.
Não garante invariância do snapshot completo (FVG, liquidez, viés e Elliott
podem legitimamente mudar), nem de históricos cuja janela inicial mudou.
Entradas devem ser OHLC válidas e cronológicas; normalização geral é pendente.

O restante da etapa 2 continua pendente: fachadas BOS/CHOCH/FVG compatíveis,
correção do CHOCH v2 invertido e revisão da política de mitigação de FVG.
Nenhum guard, risco, credencial ou configuração de execução foi alterado.
Nenhuma ordem, merge ou reinicialização foi executada. O PR #1 é independente.
