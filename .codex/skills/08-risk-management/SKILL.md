---
name: 08-risk-management
description: Risk calculation, daily limit, max trades, technical RR, technical SL, technical TP, invalid lot protection, official risk preservation.
---

# 08-risk-management

## Identificador
`risk-mgmt`

## Objetivo
Calcular e proteger risco, limite diário, RR técnico e lotes.

## Quando acionar
- Cálculo de risco para operação
- Verificação de limites de risco

## Regras
- Nunca ajustar SL para fabricar RR
- RR calculado após TP e SL técnicos
- Máximo de 3 trades por dia

## Responsabilidades
- Cálculo de risco
- Limite diário e máximo de trades
- RR técnico, SL técnico, TP técnico
- Proteção contra lotes inválidos
- Preservação de risco oficial
