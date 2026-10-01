# Relatório operacional no diário de aprendizado

O operador agora usa um ciclo único: lê as métricas, importa um diário ausente
do vault, atualiza o bloco automático no diário, grava o relatório e sincroniza
índice/contexto. O horário e `daily_learning_enabled` continuam configuráveis.

Também é possível executar `python -m src.daily_learning_diary --date 2026-09-30`.
Esse comando lê os CSVs locais e escreve relatório/diário/índice; não conecta ao
MT5 nem envia mensagens. Execute a partir da raiz, no ambiente do projeto.

## Preservação e falhas

- O bloco delimitado por `LEON_AUTO_MARKET_START` e `LEON_AUTO_MARKET_END`
  pertence ao gerador. Notas manuais devem ficar fora dele.
- A reexecução com as mesmas métricas mantém os bytes do diário idênticos.
  O relatório TXT mantém o comportamento legado de acrescentar entradas.
- A taxa de acerto continua **histórica**, não uma taxa do dia.
- Marcadores incompletos, invertidos ou duplicados produzem erro sem alteração
  do diário. Revise-os manualmente antes de repetir.
- O bloco automático não é promovido para regras/padrões de engenharia.
  `CONTEXTO_EVOLUCAO.md` marcado `CURADO_MANUALMENTE` permanece protegido.
- A gravação do diário usa substituição atômica. O ciclo completo não é uma
  transação: falhas posteriores podem deixar relatório/índice defasados até a
  próxima execução. O operador só marca o dia concluído após sucesso.
- Mantenha um único escritor. A checagem de alteração concorrente detecta
  mudanças anteriores à substituição, mas não equivale a um lock entre processos.
- O comportamento de importação do vault continua sendo apenas para arquivos
  ausentes; não há merge automático de edições conflitantes entre cópias.

## Validação da primeira etapa — 2026-09-30

34 testes passaram em Python 3.14, cobrindo diário, relatório, sync e resiliência
do operador. Dados de teste ficam em diretórios temporários. Preservação de
CRLF/BOM, conteúdo após marcadores, falha de gravação, filtro por dia, curadoria
e retry do operador foram verificados. Python 3.12 e implantação na VPS ainda
não foram validados. Nenhuma ordem ou reinicialização operacional foi executada.

O desenho foi discutido com o Grok; sua revisão foi do resumo técnico, não do
diff completo. O código e os testes foram inspecionados pelo Codex.

Próximas etapas: mapear contratos dos engines BOS/CHOCH/FVG antes de alterá-los;
validar ambiente/símbolo e execução desativada no destino antes de iniciar o
operador. A cópia antiga em `C:\XAU_ELITE_AI` não recebeu este patch.
