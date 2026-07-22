---
name: leon-daily-learning
description: Daily learning system for all LEON agents — load accumulated context, register new learnings, evolve team knowledge over time.
---

## Objective
Enable all LEON agents to learn daily from operations, decisions, errors, and patterns, accumulating context that evolves the team's knowledge.

## When to use
- At the start of every mission (load context)
- At the end of every mission (register learnings)
- When reviewing past decisions or errors

## Procedure

### 1. Load Context (start of mission)
Read these files in order:
1. `tarefas/aprendizados_diarios/CONTEXTO_EVOLUCAO.md` — accumulated patterns, decisions, errors, corrections
2. `tarefas/aprendizados_diarios/INDICE.md` — index of all daily entries
3. `tarefas/aprendizados_diarios/$(date +%F).md` — today's learning file (if exists)

### 2. Register Learnings (end of mission)
Add to `tarefas/aprendizados_diarios/YYYY-MM-DD.md`:
- Operações / Missões executadas
- Decisões tomadas
- Erros encontrados
- Correções aplicadas
- Padrões identificados
- Recomendações para outros agentes

### 3. Promote to Accumulated Context
If a pattern, error, or decision is recurring or structural, add it to:
`tarefas/aprendizados_diarios/CONTEXTO_EVOLUCAO.md`

### 4. Update Index
Keep `tarefas/aprendizados_diarios/INDICE.md` updated with new entries.

## Integration
Every agent's system prompt includes:
> "Carregue `tarefas/aprendizados_diarios/CONTEXTO_EVOLUCAO.md` no início de cada missão. Registre aprendizados ao finalizar."

## Safety
- Never log credentials, tokens, or secrets in learning files
- Never log MT5 account numbers or real account data
- Never log personal information
- Corrections must reference specific files and changes
