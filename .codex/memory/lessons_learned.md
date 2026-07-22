# Lessons Learned

## Verified Facts
- OpenCode 1.18.3 supports agents in `.opencode/agents/` with frontmatter YAML
- Skills require `SKILL.md` with `name` and `description` in frontmatter
- Commands created via `.opencode/commands/` are recognized in TUI
- Full-file JSON read/write pattern (InterestZoneStore) is a performance bottleneck
- .env file with 777 permissions exposes all credentials
- DEMO/REAL protection relies on a single conditional line of code
- Daily learning system centralizado em `tarefas/aprendizados_diarios/` com skill e comando dedicados
- 14 agentes agora participam do aprendizado diário com instruções específicas por especialidade
