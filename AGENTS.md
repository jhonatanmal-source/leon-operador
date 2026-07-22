# LEON XAU ELITE AI

## Identidade
O LEON é um **operador**, não um robô. É um sistema de análise de trading baseado em conceitos institucionais, operando com supervisão humana.

## Projeto
- **Nome**: LEON XAU ELITE AI
- **Diretório**: `/opt/leon/app`
- **Linguagem**: Python 3.12
- **OS**: Ubuntu 24.04 LTS
- **Plataforma**: MetaTrader 5 (MT5)
- **OpenCode**: 1.18.3

## Operacional Oficial
- SMC (Smart Money Concepts)
- Ondas de Elliott
- Fibonacci
- ICT (Inner Circle Trader)
- Killzones
- Regiões de interesse (Interest Zones)
- Leitura top-down
- Confirmação estrutural completa
- TP técnico
- SL técnico

## Regras Operacionais
- Momentum não é gate
- Brain Score não é gate
- Máximo de **três trades por dia**
- Notícias de alto impacto bloqueiam operação
- Entrada somente em região válida
- Uma confirmação estrutural completa pode liberar setup
- Duas confirmações são aceitáveis
- Três confirmações são preferíveis quando disponíveis
- Não entrar no meio do movimento
- Não aproximar SL para fabricar RR
- RR deve ser calculado após TP e SL técnicos
- Conta real permanece bloqueada

## Segurança
- Execução em conta real não pode ser liberada por agente
- Nenhum agente pode remover guards
- Nenhum agente pode enviar ordem durante teste
- Nenhum agente pode modificar operacional sem autorização
- Nenhum agente pode fazer commit ou push sem autorização
- Toda alteração exige diagnóstico, plano, testes, revisão e relatório
- Todo resultado deve ser baseado em evidência real

## Equipe de Engenharia

### Agentes

| Agente | Tipo | Arquivo |
|--------|------|---------|
| LEON Engineering Director | primary | `.opencode/agents/leon-engineering-director.md` |
| Senior Software Engineer | subagent | `.opencode/agents/leon-senior-software-engineer.md` |
| Software Architect | subagent | `.opencode/agents/leon-software-architect.md` |
| QA Test Engineer | subagent | `.opencode/agents/leon-qa-test-engineer.md` |
| DevOps Engineer | subagent | `.opencode/agents/leon-devops-engineer.md` |
| Security Engineer | subagent | `.opencode/agents/leon-security-engineer.md` |
| Engineering Reviewer | subagent | `.opencode/agents/leon-engineering-reviewer.md` |
| Documentation Engineer | subagent | `.opencode/agents/leon-documentation-engineer.md` |
| Observability Engineer | subagent | `.opencode/agents/leon-observability-engineer.md` |
| Performance Engineer | subagent | `.opencode/agents/leon-performance-engineer.md` |
| Refactoring Specialist | subagent | `.opencode/agents/leon-refactoring-specialist.md` |
| Release Manager | subagent | `.opencode/agents/leon-release-manager.md` |
| AI Integration Engineer | subagent | `.opencode/agents/leon-ai-integration-engineer.md` |
| Trading Systems Engineer | subagent | `.opencode/agents/leon-trading-systems-engineer.md` |

### Comandos

| Comando | Descrição |
|---------|-----------|
| `/leon-missao` | Enviar missão ao Engineering Director |
| `/leon-auditoria` | Auditoria somente leitura |
| `/leon-corrigir` | Investigar e corrigir bug |
| `/leon-testar` | Executar testes |
| `/leon-revisar` | Revisar alterações |
| `/leon-status` | Verificar status da missão |
| `/leon-retomar` | Retomar missão interrompida |
| `/leon-relatorio` | Gerar relatório consolidado |
| `/leon-aprender` | Consolidar aprendizados diários da equipe |

### Skills
- 16 skills OpenCode em `.opencode/skills/` para contexto, segurança, análise, testes, revisão, documentação e aprendizado diário.
- 25 skills Codex em `.codex/skills/` (00 a 24) com cobertura completa de todos os domínios do LEON.

## Estrutura do Projeto
- `src/` — Código fonte Python
- `tests/` — Testes
- `web_app/` — Interface web
- `docs/` — Documentação
- `config/` — Configurações
- `tarefas/` — Missões, checkpoints, memória da equipe e aprendizado diário
- `.opencode/agents/` — Definições dos agentes
- `.opencode/skills/` — Skills compartilhadas
- `.opencode/commands/` — Comandos personalizados (OpenCode)
- `.codex/` — Biblioteca profissional de skills Codex (25 skills, 14 comandos, config, memória, templates, validadores)

## Fluxo de Trabalho
1. TRIAGEM
2. DIAGNÓSTICO
3. PLANO
4. CONVOCAÇÃO
5. IMPLEMENTAÇÃO
6. TESTES
7. REVISÃO
8. SEGURANÇA
9. DOCUMENTAÇÃO
10. RELATÓRIO
11. APROVAÇÃO OU REPROVAÇÃO

## Colaboração OpenCode / Hermes / Codex
- **Workspace único:** `/opt/leon/app`.
- **OpenCode:** direção de engenharia, triagem e coordenação pela interface web.
- **Hermes:** diagnóstico, pesquisa, memória técnica e revisão assistida.
- **Codex:** implementação controlada, testes e correções reproduzíveis.
- Antes de editar, consultar `tarefas/agent_lock.json` e `tarefas/handoff_atual.md`.
- Apenas um agente pode escrever por vez; os demais permanecem em leitura ou revisão.
- O agente escritor registra missão, arquivos reservados, checkpoint e prazo no lock.
- Ao concluir ou interromper, atualiza o handoff e libera o lock.
- Revisões usam o diff existente e nunca apagam alterações de outro agente.
- Nenhum agente possui autoridade para operar MT5, enviar ordem ou reduzir guards.
- Hermes usa o perfil `leon-engineering` com aprovação inteligente.
- OpenCode mantém edição e shell sujeitos a aprovação.
- Codex trabalha no mesmo diretório com sandbox proporcional à tarefa.

## Aprendizado Diário
Todos os agentes da equipe LEON participam do sistema de aprendizado diário:

- **Contexto acumulado**: `tarefas/aprendizados_diarios/CONTEXTO_EVOLUCAO.md` — carregado no início de cada missão
- **Registro diário**: `tarefas/aprendizados_diarios/YYYY-MM-DD.md` — aprendizados do dia
- **Skill**: `leon-daily-learning` — procedimento padronizado para carregar e registrar aprendizados
- **Comando**: `/leon-aprender` — consolidar aprendizados da equipe

### Procedimento para agentes
1. Ao iniciar missão: carregue `CONTEXTO_EVOLUCAO.md` e o arquivo do dia atual
2. Ao finalizar missão: registre operações, decisões, erros, correções e padrões
3. Padrões recorrentes ou decisões estruturais devem ser promovidos para `CONTEXTO_EVOLUCAO.md`
4. Mantenha `INDICE.md` atualizado
