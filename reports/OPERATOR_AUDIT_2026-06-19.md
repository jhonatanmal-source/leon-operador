# Auditoria do Operador Leon - 19/06/2026

## Resultado

O operador estava funcional, mas possuia pontos capazes de causar parada
silenciosa, repeticao excessiva de tentativas ou atraso indevido em novas
tentativas. As correcoes foram aplicadas sem alterar a estrategia de entrada.

## Correcoes aplicadas

- Isolamento de falhas por tarefa para coleta, analise, demo, aprendizado e
  Telegram.
- Heartbeat persistente para o watchdog detectar operador travado ou degradado.
- Escrita atomica dos arquivos de estado para evitar arquivos parciais.
- Validacao de intervalos e horario configurados, com valores seguros de
  contingencia.
- Nova tentativa de Telegram permitida quando o envio anterior falhar.
- Intervalo de tentativa demo respeitado quando o spread estiver alto.
- Encerramento garantido da conexao MT5 mesmo quando ocorrer uma excecao.
- Limite diario alinhado para 3 operacoes e 3 ordens demo.
- Auditoria de setup agora diferencia violacoes historicas de modo seguro.

## Evidencias

- 6 testes de resiliencia do operador aprovados.
- 21 testes existentes de estrategia e protecao aprovados.
- Compilacao completa de `src` e `tests` aprovada.
- Conta real permanece bloqueada por `demo_only=true`.
- Em 19/06/2026: 101 setups fracos bloqueados, nenhuma ordem enviada e nenhuma
  violacao estrutural nova.

## Historico que exige memoria

Foram localizadas 7 operacoes entre 16/06/2026 e 18/06/2026 com estrutura SMC
incompleta ou neutra. As travas atuais bloqueiam esse padrao e nao houve nova
violacao em 19/06/2026.

## Refino de atividade do laboratorio

Nas 36 horas analisadas, 44 ciclos apresentaram SMC e top-down aprovados, mas
foram bloqueados apenas pela ausencia simultanea de Fibonacci e captura de
liquidez. O historico shadow equivalente possuia 2 casos comparaveis fechados,
ambos com resultado WIN 2R.

Foi criada uma faixa `LAB_SHADOW_EVIDENCE`, exclusiva para conta demo. Ela
permite que esse contexto avance somente quando:

- SMC com BOS e CHOCH estiver totalmente confirmado.
- Top-down estiver alinhado na mesma direcao.
- O historico shadow tiver pelo menos 2 casos e 70% de acerto.
- O evento BOS/CHOCH ainda nao tiver sido utilizado.
- O gatilho M5, FVG de execucao, RR, noticias e risco aprovarem a entrada.

Na primeira etapa, o limite foi mantido em 3 ordens demo por dia. Ele foi
substituido posteriormente pelo orçamento de risco descrito abaixo.
`demo_only=true` continua bloqueando conta real.

## Operacoes de correcao multi-timeframe

O macro permanece como direcao principal, mas deixou de bloquear toda correcao.
Foi adicionada a classificacao de contexto:

- `TENDENCIA`: macro, H4, H1 e M15 na mesma direcao; risco alvo de 0,5%.
- `CORRECAO`: H4, H1 e M15 alinhados contra o macro; risco alvo de 0,25%.
- `BLOQUEADO`: timeframes taticos mistos ou sem confirmacao.

O M5 permanece como gatilho final. SMC, FVG de execucao, RR, noticias, spread,
desvio de preco e perda diaria continuam obrigatorios.

O limite fixo de quantidade de ordens demo foi removido. Em seu lugar, o gestor
bloqueia novas entradas quando a soma do risco aberto com o risco planejado
superar 1% do saldo. Posicoes sem stop tambem bloqueiam novas ordens.
