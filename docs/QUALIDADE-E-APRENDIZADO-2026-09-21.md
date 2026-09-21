# Qualidade e avaliacao do aprendizado

## Entrega

A rotina de medicao foi instalada na VPS e executou com sucesso em 21/09/2026, as 19:10 (Brasilia). O agendamento roda a cada cinco minutos, separado do operador, medindo no maximo duas posicoes fechadas por execucao. Nao envia ordens nem altera risco, stop, alvo ou autonomia.

Registra MFE/MAE em unidades de risco inicial de preco, spread medio observado, preco medio executado, diferenca adversa em relacao ao preco solicitado, comissoes, swap e taxas. Observa separadamente se o preco tocou o alvo na hora seguinte ao fechamento; isso nao equivale a afirmar que outra operacao teria lucro.

Usa bid para medir liquidacao de compra e ask para venda. A consulta usa os horarios numericos dos negocios e ticks do broker com datetime UTC, conforme a [documentacao MetaQuotes](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksfrom_py). Nao mistura os horarios locais antigos do relatorio com os horarios do broker.

Historico parcial, ausencia de cotacoes e falhas de coleta ficam explicitamente identificados. A rotina nao declara cobertura completa e nao converte dado ausente em zero. Tenta no maximo tres vezes. Operacoes com aumento de posicao por ordens distintas nao recebem uma medicao simplificada incorreta.

## Primeiras medicoes confirmadas

| Operacao | MFE observado | MAE observado | Cotacoes durante a operacao |
|---|---:|---:|---:|
| Compra encerrada no stop, ticket 546657317 | 0,00R | 1,02R | 2.691 |
| Venda encerrada no TP, ticket 546233816 | 10,34R | 0,27R | 25.696 |

Esses valores sao movimentos observados de preco, nao lucro realizavel nem retorno financeiro liquido. O preco executado da compra foi 0,62 acima do solicitado; esse custo de execucao agora e visivel. Nao ha mudanca automatica de parametros baseada em duas operacoes.

## Avaliacao

Avaliacao prospectiva usa somente o registro da decisao feita na entrada e o resultado fechado confirmado. Separa escolhas alteradas pelo ranking e escolhas mantidas, sem somar moedas diferentes. Resultados de alternativas nao executadas permanecem desconhecidos. Ainda nao ha evidencia independente de melhora de rentabilidade; o estado inicial e AWAITING_PROSPECTIVE_OUTCOMES.

Relatorio diario passa a incluir medicoes disponiveis e esse estado de avaliacao. O agendamento das 23h foi preservado. Uma reformulacao visual completa do painel nao faz parte desta entrega.

## Testes e operacao

- 215 testes e 3 subtestes passaram em ambiente isolado.
- Rotina real de leitura do MT5 concluiu com sucesso e gravou as duas primeiras medicoes separadamente do registro de resultados.
- Autonomia DEMO ate desligamento manual e protecoes anteriores preservadas.
- Backup da publicacao: /opt/leon/backups/quality-20260921-191015.
- As falhas preexistentes de suites legadas descritas no relatorio anterior nao foram corrigidas nesta etapa.

## GitHub

Destino: jhonatanmal-source/leon-operador, branch backup/2026-09-21.
Enviar codigo publicado, testes, unidades de servico e documentacao. Excluir credenciais, bancos, dados privados das contas e experimentos locais ainda nao publicados.
