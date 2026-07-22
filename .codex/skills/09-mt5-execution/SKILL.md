---
name: 09-mt5-execution
description: MT5 connection, symbol resolution, DEMO account, single executor, order_send, guards, broker errors, idempotency, real account protection.
---

# 09-mt5-execution

## Identificador
`mt5-exec`

## Objetivo
Gerenciar conexão MT5, execução de ordens e proteção contra conta real.

## Quando acionar
- Configuração/verificação de conexão MT5
- Execução de ordem
- Verificação de proteção DEMO

## Responsabilidades
- Conexão MT5 e resolução de símbolo
- Conta DEMO e executor único
- order_send, guards e erros de broker
- Idempotência
- Proteção contra conta real

## Regras
- Modo seguro: nunca enviar ordem em conta real
- Verificar DEMO antes de qualquer execução
- Não remover guards de execução

## Modo padrão
Modo seguro. Nunca enviar ordem em conta real.
