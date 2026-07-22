---
name: 00-leon-core
description: Core identity, global contracts, invariants, orchestration, operational protection, critical regression detection for LEON XAU ELITE AI.
---

# 00-leon-core

## Identificador
`core-leon`

## Objetivo
Manter a identidade do LEON, contratos globais, invariantes e proteção do operacional.

## Quando acionar
- No início de qualquer missão
- Quando houver risco de violação de contrato

## Quando não acionar
- Para tarefas operacionais específicas (usar skill especializada)

## Responsabilidades
- Identidade do LEON (operador, não robô)
- Contratos globais e invariantes
- Proteção do operacional oficial
- Identificação de regressões críticas

## Entradas esperadas
- Contexto da missão
- Estado atual do checkpoint

## Saídas obrigatórias
- Diagnóstico de riscos de violação de contrato
- Lista de invariantes aplicáveis

## Arquivos protegidos
- src/ (qualquer arquivo funcional)
- AGENTS.md (protegido contra perda de regras)

## Dependências
- Nenhuma

## Procedimento
1. Verificar identidade do LEON
2. Listar contratos globais aplicáveis
3. Verificar riscos de violação
4. Reportar

## Regras contra alucinação
- Não afirmar aprovação sem evidência
- Não inventar resultados
- Não modificar estratégia
