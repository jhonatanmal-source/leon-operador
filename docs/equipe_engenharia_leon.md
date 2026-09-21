# Equipe de Engenharia LEON

## Visão Geral

A Equipe de Engenharia LEON é um conjunto de agentes especializados do OpenCode configurados para o projeto **LEON XAU ELITE AI**. A equipe segue um fluxo de trabalho estruturado com diagnóstico, plano, implementação, testes, revisão, segurança e documentação.

## Estrutura

```
.opencode/
├── agents/                      # Definições dos agentes
│   ├── leon-engineering-director.md        # Supervisor (primary)
│   ├── leon-senior-software-engineer.md    # Subagent
│   ├── leon-software-architect.md          # Subagent (read-only)
│   ├── leon-qa-test-engineer.md            # Subagent
│   ├── leon-devops-engineer.md             # Subagent
│   ├── leon-security-engineer.md           # Subagent (read-only)
│   ├── leon-engineering-reviewer.md        # Subagent
│   ├── leon-documentation-engineer.md      # Subagent
│   ├── leon-observability-engineer.md      # Subagent
│   ├── leon-performance-engineer.md        # Subagent
│   ├── leon-refactoring-specialist.md      # Subagent
│   ├── leon-release-manager.md             # Subagent
│   ├── leon-ai-integration-engineer.md     # Subagent
│   └── leon-trading-systems-engineer.md    # Subagent (read-only)
├── skills/                      # Skills compartilhadas (15)
│   ├── leon-project-context/
│   ├── leon-safety-contract/
│   ├── leon-root-cause-analysis/
│   ├── leon-testing-protocol/
│   ├── leon-code-review/
│   ├── leon-security-review/
│   ├── leon-reporting-standard/
│   ├── leon-vps-operations/
│   ├── leon-mt5-safety/
│   ├── leon-architecture-analysis/
│   ├── leon-observability-standard/
│   ├── leon-release-checklist/
│   ├── leon-resume-from-checkpoint/
│   ├── leon-operational-contract/
│   └── leon-change-impact-analysis/
└── commands/                    # Comandos personalizados (8)
    ├── leon-missao.md
    ├── leon-auditoria.md
    ├── leon-corrigir.md
    ├── leon-testar.md
    ├── leon-revisar.md
    ├── leon-status.md
    ├── leon-retomar.md
    └── leon-relatorio.md
```

## Lista de Agentes

### Supervisor
| Agente | Modo | Descrição |
|--------|------|-----------|
| LEON Engineering Director | primary | Coordenador central, classifica missões, escolhe especialistas, controla checkpoints |

### Especialistas
| Agente | Modo | Descrição |
|--------|------|-----------|
| Senior Software Engineer | subagent | Bugs, causa raiz, implementação, refatoração |
| Software Architect | subagent (read-only) | Arquitetura, dependências, acoplamento, diagramas |
| QA Test Engineer | subagent | Testes, validação, regressão, áreas críticas |
| DevOps Engineer | subagent | Infraestrutura, VPS, Docker, backups, deploy |
| Security Engineer | subagent (read-only) | Segurança, credenciais, firewall, tokens |
| Engineering Reviewer | subagent | Revisão de alterações, git diff, regressões |
| Documentation Engineer | subagent | Documentação, AGENTS.md, README, relatórios |
| Observability Engineer | subagent | Logs, métricas, health checks, rastreabilidade |
| Performance Engineer | subagent | CPU, RAM, disco, profiling, gargalos |
| Refactoring Specialist | subagent | Duplicação, complexidade, código morto |
| Release Manager | subagent | Prontidão, testes, segurança, rollback |
| AI Integration Engineer | subagent | OpenRouter, prompts, fallback, custos |
| Trading Systems Engineer | subagent (read-only) | SMC, Elliott, Fibonacci, ICT, MT5, risco |

## Como Usar

### Enviar uma missão
Na TUI do OpenCode, digite:
```
/leon-missao <descrição da missão>
```

### Executar auditoria
```
/leon-auditoria <área>
```

### Corrigir bug
```
/leon-corrigir <descrição do bug>
```

### Executar testes
```
/leon-testar <escopo opcional>
```

### Revisar alterações
```
/leon-revisar
```

### Verificar status
```
/leon-status
```

### Retomar missão
```
/leon-retomar
```

### Gerar relatório
```
/leon-relatorio <missão>
```

## Regras

1. Toda alteração exige diagnóstico, plano, testes, revisão e relatório.
2. Nenhum agente pode remover guards, enviar ordens ou liberar conta real.
3. Nenhum agente pode modificar estratégia, risco, TP, SL sem autorização.
4. Nenhum agente pode fazer commit ou push sem autorização.
5. Todo resultado deve ser baseado em evidência real.
6. Agentes read-only não modificam arquivos.

## Segurança

- Conta real permanece bloqueada
- Execução em conta real não pode ser liberada por agente
- Credenciais expostas: registrar apenas o caminho, não o valor
- Skills de segurança devem ser carregadas antes de operações críticas

## Checkpoints

Checkpoints são salvos em:
- `tarefas/checkpoint_equipe_leon.json` (formato JSON para máquina)
- `tarefas/checkpoint_equipe_leon.md` (formato legível)

Cada checkpoint contém: fase atual, tarefas concluídas, arquivos criados, pendências, riscos e próxima ação.

## Memória Compartilhada

`tarefas/memoria_engenharia/` contém:
- `decisoes_arquitetura.md` — Decisões arquiteturais registradas
- `bugs_conhecidos.md` — Bugs conhecidos
- `correcoes_validadas.md` — Correções já validadas
- `riscos_abertos.md` — Riscos em aberto
- `divida_tecnica.md` — Dívida técnica identificada
- `padroes_do_projeto.md` — Padrões do projeto
- `comandos_validados.md` — Comandos validados
- `testes_criticos.md` — Áreas críticas de teste
- `incidentes.md` — Registro de incidentes
- `proximas_prioridades.md` — Próximas prioridades

## Como Retomar uma Missão

1. Leia `tarefas/checkpoint_equipe_leon.json`
2. Identifique `current_phase` e `next_action`
3. Verifique tarefas concluídas em `completed_tasks`
4. Não repita trabalho já feito
5. Continue da próxima tarefa pendente
6. Atualize o checkpoint após cada fase

Ou use o comando `/leon-retomar` na TUI.

## Como Adicionar um Agente

1. Crie `{nome}.md` em `.opencode/agents/`
2. Adicione frontmatter YAML com `description` e `mode`
3. Defina permissões apropriadas
4. Adicione à tabela em `AGENTS.md`
5. Valide o reconhecimento na TUI

## Como Desativar um Agente

Adicione `disable: true` no frontmatter do agente.

## Como Validar

1. Verificar sintaxe do frontmatter YAML
2. Confirmar que o agente aparece no `@` menu da TUI
3. Confirmar que permissões estão corretas
4. Testar comando se aplicável
5. Verificar git diff

## Problemas Conhecidos

- Alguns agentes podem não ser reconhecidos se o OpenCode não estiver configurado para ler `.opencode/agents/`
- Comandos precisam ser testados na TUI interativamente
- Skills dependem de nome e descrição corretos no SKILL.md
