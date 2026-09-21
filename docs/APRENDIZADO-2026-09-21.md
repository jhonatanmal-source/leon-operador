# Correcao do aprendizado - 21/09/2026

## Publicado e verificado

- Politica `smc_opportunity_v1`: agrupamento por ativo, direcao, modelo SMC e contexto. Nomes de ondas permanecem nos registros, mas nao fragmentam o ranking.
- Cada conta/regiao conta como uma oportunidade. Tickets e resultados financeiros originais foram preservados. Media dos retornos R dos tickets da regiao e uma estatistica da oportunidade, nao retorno da conta.
- Posicoes repetidas nao inflam amostras. Identidades ausentes nao contam como oportunidades; modelos/contextos nao identificados permanecem neutros.
- Abaixo de quatro oportunidades independentes no grupo, a prioridade permanece neutra. Isso nao bloqueia um setup valido. Acima disso, ranking exploratorio com a mesma regularizacao n/(n+20), sem alegacao de vantagem validada.
- Comparacao entre candidato escolhido e candidato valido mais recente registrada na selecao e preservada nos metadados das ordens e nos resultados fechados. Nao representa lucro contrafactual.
- Relatorio diario e evidencias do Obsidian distinguem observacoes, memoria legada, tickets, oportunidades e atribuicao de escolhas. Status operacional mostra oportunidades e ultima comparacao disponivel.

## Historico atual

Sete operacoes fechadas representam cinco oportunidades independentes em tres grupos:

| Grupo | Tickets | Oportunidades |
|---|---:|---:|
| Compra / Order Block / Tendencia | 3 | 2 |
| Compra / CHOCH + Order Block / Tendencia | 1 | 1 |
| Venda / Order Block / Correcao | 3 | 2 |

Nenhum grupo tem amostra suficiente para receber prioridade diferente de zero. Nao foi reduzido o minimo para fabricar aprendizado. O historico foi auditado por ordem de fechamento, sem gravar resultados artificiais. Essa auditoria nao e backtest de entradas nem validacao fora da amostra.

## Verificacao

- 194 testes e 3 subtestes focados passaram em copia isolada.
- Em suites legadas mais amplas, 2 falhas e 17 erros de fixtures foram reproduzidos tambem na copia do codigo anterior: expectativa de lote, status Telegram sem heartbeat e fixtures do executor com API removida. Nao foram introduzidos pela alteracao; nao foram corrigidos nesta entrega.
- Teste de integracao da selecao: somente pre-operacao aberta, nao executada e com evidencia aprovada entra no ranking. Nenhuma ordem real ou demo enviada pelos testes.
- Publicacao em 21/09 as 18:05; operador, Telegram e web ativos.
- Heartbeat 18:05:47: nenhuma tarefa falhou, demo autorizada ate revogacao manual, aguardando setup.
- Configuracao, autonomia, risco, stop e alvo nao alterados.
- Backup VPS: `/opt/leon/backups/opportunity-learning-20260921-180533`.

## Limites e proximos passos

Nao foi comprovada melhora de rentabilidade. A nova atribuicao permite observar se o ranking realmente altera escolhas futuras. Ainda faltam medicao de excursao por ticks (MFE/MAE), comparacao independente da rentabilidade e reformulacao visual do painel. Os experimentos locais anteriores nao foram publicados junto desta correcao.
