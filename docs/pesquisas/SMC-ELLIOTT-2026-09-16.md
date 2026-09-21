# Entrega: SMC, Elliott, aprendizado e backtest

## Resultado final

Correcao de entrada por CHOCH e separacao do aprendizado instaladas na VPS em 16/09/2026. Apenas demo, dentro da autonomia anteriormente autorizada. A implementacao passou nos testes; o desempenho financeiro do setup NAO foi aprovado pelo backtest.

Nao foi enviada ordem artificial para demonstrar funcionamento. Servico ativo e sinal elegivel nao equivalem a uma ordem confirmada no MT5. Na verificacao de 07:49 de Sao Paulo, autonomia e risco estavam autorizados, sem falha de tarefas; aguardava confirmacao de zona/liquidez.

Atualizacao final: verificacao somente leitura diretamente no historico MT5 confirmou a ordem automatica demo `543639586`, COMPRA XAUUSD, registrada as 10:54:49 de 16/09/2026. Execucao a 4338,44, volume 0,86; fechamento por stop a 4337,76. Perda de preco US$ 58,48 e comissoes US$ 5,22: liquido **-US$ 63,70**. Nao estava mais aberta. O aprendizado contem exatamente um fechamento, modelo `ORDER_BLOCK_RETEST`, contexto `TENDENCIA`, retorno -1,2995R. Portanto, houve execucao efetiva e reconciliacao; isso nao demonstra rentabilidade. A perda realizada inclui custos e derrapagem, podendo superar o risco nominal calculado antes da ordem.

Na analise das 12:21, contexto e estrutura passaram, mas o plano aguardava novo reteste M5; a zona anterior estava invalidada. Nao foi forcada entrada nem reativada zona invalida.

## O que foi corrigido

1. CHOCH com deslocamento e reteste prospectivo de OB ganhou caminho proprio. Nao depende de inventar um BOS posterior nem de exigir FVG em toda entrada.
2. Analise, pre-operacao e executor conferem a mesma zona canonica. Sem reteste, zona vencida, invalidada, de outro ativo ou ja utilizada, essa alternativa nao autoriza entrada.
3. Estatisticas de aprendizado agora distinguem modelo de entrada e contexto CORRECAO/TENDENCIA. O teste anterior contava quatro categorias como quatro amostras iguais; corrigido para uma amostra correspondente.
4. O modelo vem da evidencia validada antes da selecao, acompanha a ordem e e recuperado no fechamento real da demo. Dados antigos sem identificacao ficam UNSPECIFIED; nao sao adivinhados.
5. Relatorio diario e grupos do Obsidian usam essa separacao. O aprendizado continua exploratorio: nao e consciencia, nao garante melhora e nao altera sozinho risco, SL ou TP.

Elliott permanece contexto multigrau, sem veto por contagem incompleta. Correcoes e retomadas continuam autorizadas. Risco por ordem, stop diario, giveback de lucro fechado, limite de posicoes abertas e bloqueio de conta real preservados.

## Backtest apos os ajustes finais

Exportacao nova e somente leitura do MT5. Janela de 60 dias do historico da corretora, de 18/07 a 16/09/2026, 11.590 avaliacoes M5. Horario bruto da corretora nao foi certificado como UTC. Fonte final copiado para ambiente isolado apos a instalacao.

| Indicador | Resultado |
|---|---:|
| Operacoes encerradas | 54 |
| Vitorias / perdas | 13 / 41 |
| Acerto | 24,07% |
| Resultado liquido | -8,1441R |
| Media por operacao | -0,1508R |
| Fator de lucro | 0,806 |
| Maior queda acumulada em resultados fechados | 18,8305R |
| Posicoes abertas no final | 0 |

R e o risco inicial normalizado, nao um valor monetario nem um percentual direto da conta.

| Modelo / contexto | Operacoes | Vitorias | Resultado aproximado |
|---|---:|---:|---:|
| CHOCH + OB / correcao | 11 | 2 | -4,48R |
| CHOCH + OB / tendencia | 17 | 6 | +4,03R |
| BOS + OB / correcao | 12 | 2 | -5,65R |
| BOS + OB / tendencia | 14 | 3 | -2,04R |

Conclusao: reconhece mais entradas que a implementacao anterior, mas o conjunto continua negativo. Nao ha justificativa para conta real. O recorte positivo nao e validacao independente e nao foi usado para proibir silenciosamente as correcoes solicitadas pelo usuario.

O replay registrou 287 zonas, 116 ciclos com zona confirmada, 145 aprovacoes do setup, 57 planos e 54 entradas simuladas. Houve tres recusas por preco/relacao risco-retorno no preenchimento. As contagens de gates se sobrepoem; nao devem ser somadas como motivos exclusivos.

Limitacoes: simulacao do setup, nao de toda a operacao da corretora; grade M5 em vez de agendamento real; custos assumidos de 0,02R, spread historico e derrapagem de um ponto; sem swaps, noticias historicas, rejeicoes do broker ou drawdown flutuante completo. Usa retorno normalizado, sem capitalizacao integral. A alteracao no aprendizado foi testada separadamente; este replay nao mede adaptacao online ou ranking com historico real de fechamentos. Grande parte da amostra ja foi examinada em estudos anteriores.

Artefato: `backtest-final-2026-09-16.json`, com operacoes, motivos, metadados e hashes dos fontes. Reproducao isolada na VPS: `/tmp/leon-final-20260916/backtest_v24.py --choch`. Nenhum resultado simulado foi adicionado ao aprendizado real.

## Pesquisa: conceito nao e condicao universal

O [guia de modelos enviado pelo usuario](https://tradingstrategyguides.com/the-ultimate-guide-to-smc-entry-models-trading-like-the-smart-money/) distingue reversao apos sweep/CHOCH, continuacao em OB e entrada pelo FVG. No exemplo de reversao, OB ou FVG sao alternativas; na continuacao, o FVG e apresentado como confluencia ideal. Essa leitura nao sustenta uma exigencia global de FVG para qualquer entrada. O artigo e material educacional, sem validacao estatistica do nosso sistema.

O PDF de Marcos Leitao/@marraik, fornecido pelo usuario, foi lido em texto nas 36 paginas. As figuras das paginas 14 e 33-35 foram inspecionadas. Elas separam contexto maior, regiao, chegada do preco, mudanca estrutural no menor e reteste. A v2.8 cobre a alternativa CHOCH/reteste M15-M5, mas NAO implementa integralmente o encadeamento de zonas H4/H1 mostrado no material.

A [Waveopedia](https://www.elliottwave.com/waveopedia/) diferencia graus e movimentos corretivos/impulsivos. A [secao sobre correcoes](https://www.elliottwave.com/waveopedia/corrective-waves/) reconhece sua identificacao dificil antes da conclusao. A decisao de usar Elliott como contexto e SMC como gatilho e nosso contrato de projeto; nao uma garantia de rentabilidade extraida desses textos.

O [BabyPips enviado](https://www.andrerj.com.br/_pdf/BabyPips.pdf) tem 388 paginas e se identifica como traducao comunitaria, nao edicao oficial atual. Foram consultados sumario e trechos selecionados de Elliott, sistemas, gatilho, diario, lote e stop; nao se afirma leitura integral. Paginas 169, 316, 320, 338 e 346 tambem foram verificadas visualmente. Aplicacoes relevantes: separar area de interesse de gatilho; manter registros por categoria; definir invalidacao tecnica antes de dimensionar posicao. Expressoes imprecisas da traducao, como inferir taxa de acerto a partir de RR, nao foram convertidas em regras.

O [BIS descreve um mercado FX fragmentado](https://www.bis.org/publications/fx-trade-execution-through-lens-triennial), com diversos canais de execucao. Inferir intencoes exatas de bancos apenas por um candle nao e observacao direta de suas ordens. No sistema, OB, liquidez e deslocamento sao caracteristicas calculadas do preco, nao provas de quem negociou.

O estudo [The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) fundamenta a cautela com escolha de parametros apos observar resultados. Nao basta experimentar variacoes ate aparecer um historico positivo.

## Matriz do operacional

| Componente | Situacao real |
|---|---|
| Contexto Elliott H1/M15 e H4/H1 | Existente; contagem incompleta nao impede sozinha |
| BOS + OB + reteste | Existente, testado no replay |
| CHOCH + deslocamento + OB + reteste | Instalado v2.8, testado no replay |
| FVG | Modelo separado existente; nao condicao global do OB |
| Correcao contra macro | Permitida quando reconhecida no contexto menor; resultado historico fraco |
| Zona H4/H1 tocada -> CHOCH M5 -> OB M5 | Implementacao completa ainda pendente; direcao H4 nao substitui zona H4 |
| Breaker, IFVG, OTE e outros nomes | Nao ativados como novos modelos; requerem contrato e teste proprio |
| Aprendizado por modelo/contexto | Corrigido; fechamentos confirmados, sem misturar simulacoes |

## Prioridades tecnicas restantes

1. Mapear zonas de tempo maior de maneira causal, com registro de criacao, toque e invalidacao; testar sua associacao a estrutura de tempo menor. Nao transformar qualquer CHOCH em entrada.
2. Separar expiracao de sinal e validade da regiao. A regra atual vence a zona com o sinal; qualquer rearmamento precisa de um novo evento observado, sem duplicidade nem reteste retroativo.
3. Avaliar alvo e stop conforme modelo e grau. Nao aproximar stop para fabricar RR nem projetar alvo inexistente. A exigencia atual de dois alvos merece estudo separado.
4. Validar em periodo novo, custos mais severos e execucao completa. Nao apresentar o recorte vencedor deste backtest como melhoria provada.

Essas prioridades estao documentadas, nao marcadas como implementadas. A entrega tecnica atual nao significa que todo o material de Forex foi incorporado ou que o operacional esteja pronto para dinheiro real.

## Videos e imagens

Foram tentados os links `QEHLxm90hZI`, `z0b_kfJkluw` (duas playlists) e `-axFOsodgOQ`. O acesso web retornou limitacao do YouTube e nao forneceu transcricoes. Nao foi afirmado que essas aulas foram assistidas. O [canal de referencia do autor](https://linktr.ee/marraik) foi localizado, e seu PDF fornecido foi a referencia verificavel.

A pesquisa visual por SMC/Elliott retornou diagramas com regras diferentes, inclusive variantes com e sem BOS adicional. Resultados de imagem nao constituem um padrao unico nem prova de lucratividade. As figuras efetivamente inspecionadas para a comparacao foram as dos PDFs citados.

## Verificacao e backups

- Instalacao final: 258 testes e 14 subtestes passaram.
- Simulador: 15 testes adicionais passaram, incluindo ausencia de acesso ao candle futuro, preenchimento com gap e prioridade ao stop quando SL/TP coincidem no candle.
- Backup da alternativa CHOCH: `/opt/leon/backups/choch-retest-20260916-103736`.
- Backup da separacao do aprendizado: `/opt/leon/backups/learning-model-context-20260916-104627`.
- Pesquisa e historico de engenharia ficam separados dos resultados reais usados no aprendizado.
