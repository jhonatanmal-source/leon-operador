# Contexto de Evolução — Aprendizados Acumulados

Este arquivo é carregado por todos os agentes ao iniciar uma missão.
Contém padrões, decisões, erros e correções acumulados que evoluem o conhecimento da equipe.

## Como usar
- Leia este arquivo no início de cada missão
- Adicione novos aprendizados ao final do dia em `tarefas/aprendizados_diarios/YYYY-MM-DD.md`
- Apenas padrões recorrentes e decisões estruturais devem ser promovidos para cá

---

## Padrões Identificados

- **Paths Windows legados**: sistemas migrados do Windows para Linux podem conter `C:/XAU_ELITE_AI/` hardcoded — verificar `log_engine.py`, `pre_operation_engine.py`, `leon.py` em revisões
- **MagicMock sem atributos numéricos**: `float(MagicMock())` retorna `1.0` — sempre mockar `volume_step`, `volume_min`, `volume_max` em testes de executor MT5
- **Asserts literais de import**: testes que verificam strings de import (`"from .mt5_order_executor import"`) quebram se o padrão de import mudar — preferir verificação indireta
- **rpyc version mismatch**: mt5linux (1.0.3) força `rpyc==5.2.3` na instalação, mas servidor wine MT5 usa `rpyc 6.0.2`. Sempre reinstalar `rpyc>=6.0` após instalar mt5linux.
- **Autonomy scope**: state file (`autonomy_state.json`) tem precedência sobre config.ini. Alterar ambos ao modificar escopo.
- **Sem sudo**: usuário `leon` não está no sudoers. Serviços systemd devem ser instalados como `systemd-run --user` ou via crontab.

## Decisões Estruturais

- Sistema de aprendizado diário centralizado em `tarefas/aprendizados_diarios/`
- Contexto de evolução compilado em `CONTEXTO_EVOLUCAO.md` para carregamento rápido
- Skill `leon-daily-learning` criada para padronizar o procedimento entre agentes
- Comando `/leon-aprender` criado para consolidar aprendizados

## Erros Recorrentes

- Permissions matrix (`permissions_matrix.md`) desatualizada — 5 agentes com bash:allow mas documentados como ask
- `leon-observability-engineer.md` continha instrução residual da fase de criação
- `agent_lock.json` mantinha metadados de missão já concluída
- **rpyc downgrade**: instalação do mt5linux faz downgrade do rpyc (6.0.2→5.2.3), quebrando conexão MT5
- **state file precedence**: alterar config.ini sem atualizar state file não aplica mudanças
- **sudo não disponível**: tentar instalar serviços systemd requer sudo; usar `systemd-run --user`

## Correções Aplicadas

| Data | Arquivo | Correção |
|------|---------|----------|
| 2026-07-22 | — | Permissions matrix atualizada com linhas explícitas para todos os agentes |
| 2026-07-22 | — | Instrução residual removida do agente de observabilidade |
| 2026-07-22 | — | agent_lock.json limpo (mission_id, reserved_files, started_at zerados) |
| 2026-07-22 | `config.ini` | `scope = execution` → `scope = demo_execution` para liberar execução demo |
| 2026-07-22 | `data/autonomy_state.json` | `scope` corrigido para `demo_execution` (state file tinha precedência) |
| 2026-07-22 | venv | rpyc reinstalado 5.2.3 → 6.0.2 para compatibilidade com servidor wine MT5 |
| 2026-07-22 | systemd --user | Operador iniciado como `leon-operator.service` transient (sem sudo) |

## Contratos Protegidos (relembre)
- Conta real sempre bloqueada
- Nenhum agente pode enviar ordens MT5
- Nenhum agente pode remover guards
- Toda alteração exige diagnóstico, plano, testes, revisão e relatório
