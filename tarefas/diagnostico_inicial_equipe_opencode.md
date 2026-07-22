# Diagnóstico Inicial — Equipe de Engenharia LEON

## Ambiente

| Item | Valor |
|------|-------|
| Diretório atual | `/opt/leon/app` |
| Projeto | LEON XAU ELITE AI |
| OpenCode versão | 1.18.3 |
| Sistema operacional | Ubuntu 24.04.4 LTS |
| Python | 3.12.3 |
| Modelo configurado | `opencode/deepseek-v4-flash-free` |
| Modelo small | `opencode/north-mini-code-free` |

## Estrutura encontrada

- `src/` — Código fonte Python do LEON (130+ arquivos)
- `tests/` — Testes
- `web_app/` — Aplicação web
- `docs/` — Documentação inicial
- `config/` — Configurações
- `reports/` — Relatórios
- `tools/` — Ferramentas
- `studies/` — Estudos
- `backups/` → `/opt/leon/backups`
- `data/` → `/opt/leon/data`
- `logs/` → `/opt/leon/logs`
- `.env` → `/opt/leon/config/.env`

## Arquivos existentes (relevantes)

| Arquivo | Status |
|---------|--------|
| `AGENTS.md` | Não existe |
| `.opencode/` | Não existia (criado agora) |
| `opencode.json` | Configuração global em `~/.config/opencode/opencode.json` |
| `LEON_PRINCIPIOS.md` | Existe |
| `REGRAS_CODEx.md` | Existe |
| `README.md` | Existe |
| `ESTRUTURA_PROJETO.md` | Existe |

## Possíveis conflitos

- Nenhum arquivo de agente, skill ou comando pré-existente
- Configuração OpenCode é global, não por projeto
- `AGENTS.md` precisa ser criado do zero

## Plano de criação

1. Fase 0: Diagnóstico ✔
2. Fase 1: Formato OpenCode 1.18.3 — Markdown em `.opencode/agents/`, `.opencode/skills/`, `.opencode/commands/`
3. Fase 2: Supervisor Principal (Engineering Director)
4. Fase 3: 13 Agentes Especialistas
5. Fase 4: 15 Skills Compartilhadas
6. Fase 5: AGENTS.md
7. Fase 6: 8 Comandos Operacionais
8. Fase 7: Memória Compartilhada (10 arquivos)
9. Fase 8: Checkpoint JSON + MD
10. Fase 9-14: Validação, Simulações, Documentação, Relatório Final

## Limitações da versão instalada (OpenCode 1.18.3)

- Suporta agentes em Markdown (frontmatter YAML)
- Suporta primary e subagent modes
- Suporta skills via `SKILL.md`
- Suporta comandos via Markdown em `.opencode/commands/`
- Suporta permissões granulares por agente
- Suporta `model` override por agente
- Suporta `steps` (max steps)
- Suporta `hidden` para subagentes
- Suporta `color` para personalização visual
- Sem limitações conhecidas que impeçam a execução do plano

## Data do diagnóstico

2026-07-20 04:20 UTC
