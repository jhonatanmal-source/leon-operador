# Checklist diária — LEON demo FTMO

Esta checklist serve para Codex, Grok e operador humano acompanharem o sistema sem transformar frequência de trades em objetivo. Um dia sem entrada é válido quando os gates não confirmam setup.

## 1. Antes da sessão

- [ ] MT5 aberto, conectado à conta **demo** e com tick recente de XAUUSD.
- [ ] Heartbeat do operador `ONLINE`, com `execution_authorized: true` somente durante a autonomia concedida.
- [ ] `FTMO_ENTRY_BUDGET_OK` ou outro motivo explícito, sem exceção silenciosa.
- [ ] Calendário econômico aprovado e fora de janela de alto impacto.
- [ ] Nenhuma posição, ordem pendente ou envio `INDETERMINADA` sem reconciliação humana.

## 2. Qualidade do sinal

- [ ] Leitura top-down registrada como `ALINHADO`, `MISTO`, `LATERAL` ou `SEM DADOS`.
- [ ] `LATERAL`, `MISTO` e `SEM DADOS` permanecem bloqueios; nunca contam como permissão.
- [ ] Região, Fibonacci/liquidez, estrutura SMC e relação risco/retorno passaram nos gates existentes.
- [ ] Existe pré-operação aberta e identificável antes de qualquer tentativa de ordem.

## 3. Resultado do ciclo

- [ ] Registrar um de: `ENTRADA_DEMO`, `AGUARDAR_SETUP`, `BLOQUEIO_DE_RISCO`, `FALHA_DE_DADOS`.
- [ ] Para `AGUARDAR_SETUP`, registrar o motivo estável (por exemplo `FIBONACCI_OU_LIQUIDEZ_NAO_CONFIRMADOS`).
- [ ] Para `FALHA_DE_DADOS`, registrar fonte, horário e ação de recuperação; não reclassificar como lateralidade.
- [ ] Para ordem ambígua, manter `INDETERMINADA` e reconciliar no MT5 antes de liberar nova tentativa.

## 4. Fechamento diário

- [ ] Conferir `decision_diagnostic.json`, heartbeat e log do operador.
- [ ] Verificar limite diário, exposição aberta e número de entradas da sessão.
- [ ] Revisar pré-operações observadas/fechadas e registrar aprendizado sem alterar guards por pressão de frequência.
- [ ] Anotar uma melhoria concreta, apenas se houver evidência no log ou em teste reproduzível.

## 5. Papel de cada revisor

| Responsável | Verifica | Não faz |
| --- | --- | --- |
| Codex | testes, logs, integração MT5/FTMO, regressões | liberar conta real, forçar entrada, reduzir guard |
| Grok | revisão do diff, contratos de segurança, riscos de regressão | alterar repositório ou autorizar ordem |
| Operador humano | status da conta demo, autonomia e decisão de continuidade | ignorar bloqueio para obter trade diário |

## Meta operacional

Todos os dias deve haver **um ciclo de análise auditável**, mesmo que o resultado seja aguardar. A meta é aumentar a qualidade dos setups válidos e reduzir bloqueios causados por falha técnica; não é fabricar uma operação diária.
