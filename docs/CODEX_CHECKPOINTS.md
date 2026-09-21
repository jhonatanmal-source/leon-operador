# Codex Checkpoints

## Format
Checkpoints are stored in `tarefas/`:
- JSON: `tarefas/checkpoint_codex_atual.json`
- Markdown: `tarefas/checkpoint_codex_atual.md`
- Progress: `tarefas/progresso_codex.md`

## Fields
- mission_id, mission_title
- started_at, updated_at
- current_phase
- completed_steps, pending_steps
- files_created, files_modified
- tests_executed, test_results
- blockers, warnings
- next_action
- selected_skills
- rollback_reference

## Resume Procedure
1. Read checkpoint
2. Verify Git state
3. Skip completed tasks
4. Continue from next pending step
5. Record resumption
