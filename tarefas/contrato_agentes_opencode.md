# Contrato de Agentes OpenCode — LEON XAU ELITE AI

## Formato Oficial

**OpenCode versão 1.18.3**

### Agentes
- **Local**: `.opencode/agents/` (projeto) ou `~/.config/opencode/agents/` (global)
- **Formato**: Markdown com frontmatter YAML
- **Frontmatter necessário**: `description`, `mode`
- **Frontmatter opcional**: `temperature`, `steps`, `model`, `permission`, `color`, `hidden`, `top_p`, `disable`
- **Tipos**: `primary`, `subagent`, `all`

### Skills
- **Local**: `.opencode/skills/<nome>/SKILL.md`
- **Formato**: Markdown com frontmatter YAML
- **Frontmatter necessário**: `name`, `description`
- **Regras**: nome em lowercase, sem espaços, hífen único

### Comandos
- **Local**: `.opencode/commands/<nome>.md`
- **Formato**: Markdown com frontmatter YAML
- **Frontmatter**: `description`, `agent`, `model`, `subtask`

## Decisões

1. Usar `.opencode/agents/` para agentes do projeto
2. Usar `.opencode/skills/` para skills do projeto
3. Usar `.opencode/commands/` para comandos do projeto
4. Agente supervisor será `primary` mode
5. Agentes especialistas serão `subagent` mode
6. Skills seguirão padrão `nome-com-hifens`

## Data

2026-07-20 04:21 UTC
