---
name: leon-resume-from-checkpoint
description: Resume interrupted missions from the last valid checkpoint — read checkpoint file, verify completed tasks, continue from next action.
---

## Objective
Enable seamless mission resumption after interruption.

## When to use
- When retaking an interrupted mission
- When a mission handoff occurs between agents

## Procedure
1. Read `tarefas/checkpoint_equipe_leon.json`
2. Identify `current_phase` and `next_action`
3. Verify which tasks are completed
4. Do not repeat completed work
5. Continue from the next pending task
6. Update checkpoint with resumption timestamp

## Criteria
- Do not re-execute completed tasks
- Validate checkpoint integrity before continuing
- If checkpoint is invalid, restart from last known good state
