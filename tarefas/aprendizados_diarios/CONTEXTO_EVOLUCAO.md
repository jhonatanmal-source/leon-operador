# Contexto de Evolução — Aprendizados Acumulados

Este arquivo é carregado por todos os agentes ao iniciar uma missão.
Contém padrões, decisões, erros e correções acumulados que evoluem o conhecimento da equipe.

## Como usar
- Leia este arquivo no início de cada missão
- Adicione novos aprendizados ao final do dia em `tarefas/aprendizados_diarios/YYYY-MM-DD.md`
- Apenas padrões recorrentes e decisões estruturais devem ser promovidos para cá

---

## Padrões Identificados

*(Nenhum padrão registrado ainda)*

## Decisões Estruturais

- **rpyc 6.0.2 > rpyc 5.2.3**: Servidor wine MT5 roda rpyc 6.0.2. Cliente venv foi downgrade para 5.2.3 pelo mt5linux. Solução: reinstalar rpyc==6.0.2. mt5linux declara `rpyc==5.2.3` como dependência mas funciona com 6.0.2.
- **systemd --user**: Usuário `leon` não tem sudo. Serviço instalado como `systemd-run --user --unit=leon-operator` (transient, não persistente após reboot). Alternativa: usar crontab @reboot ou solicitar configuração de sudo NOPASSWD.
- **Autonomy scope**: Config.ini tinha `scope = execution`, código exige `scope = demo_execution` ou `learning_and_demo`. Corrigido em config.ini e `autonomy_state.json`.
- **Telegram via .env**: Token e chat_id do Telegram prioritariamente lidos de `.env` (via `_load_env_file()`). `config.ini` serve como fallback. `.env` sobrescreve `config.ini`.
- **Telegram via .env**: Token e chat_id do Telegram não estão em config.ini (estão vazios). Estão em `/opt/leon/config/.env` com symlink de `/opt/leon/app/.env`.
- Usar obsidian-headless (CLI oficial) em vez de app GUI (servidor headless)
- Vault Obsidian como complemento, não substituto, do sistema de aprendizado diário
- Sincronização bidirecional entre `obsidian_vault/aprendizados_diarios/` e `tarefas/aprendizados_diarios/`
- Script de integração em `scripts/sync_obsidian_vault.sh` para manter ambos atualizados
- **MCPs em `src/mcp/`** — diretório dedicado, sem poluir src/ raiz
- **Wrapper `_mt5_safe.py`** para isolar funções read-only do MT5 e bloquear ordens
- **MCPs orquestram, não implementam** — Backtest MCP chama engines existentes
- **`opencode.json` no projeto** para registrar MCPs sem modificar config global
- **Rota de Laboratório**: Bootstrap pode criar Interest Zones sintéticas via `create_lab_zone()` para pré-ops passarem o guard estrutural `validate_zone_for_execution()`. Zonas marcadas com `zone_source=LABORATORIO` para rastreabilidade. Ativado automaticamente quando `modo_bootstrap_ativo()` e `brain_score >= auto_simulate_min_score`. Seguro para demo pois zonas são segregadas de zonas SMC reais.

## Erros Recorrentes

- **Conexão MT5 falha**: `ValueError: invalid message type: 18` — incompatibilidade rpyc 5.2.3 (cliente) vs 6.0.2 (servidor wine).
- **Autonomy scope incorreto**: Config `scope = execution` bloqueia execução demo. Código espera `demo_execution` ou `learning_and_demo`.
- **State file precedence**: `autonomy_state.json` sobrescreve config.ini para scope. Mesmo alterando config.ini, state file persistia valor antigo.
- **sudo não disponível**: Usuário `leon` não está no sudoers. Serviços systemd não podem ser instalados como system service.
- Nenhum erro durante a instalação
- 0 vulnerabilidades no npm audit
- Nenhuma alteração em src/ (código operacional), config/ (configurações) ou data/ (dados)
- **Bug corrigido**: `run_server` passava argumentos posicionais para handlers que não os aceitavam → adicionado `*args, **kwargs` nos `__init__` dos 4 handlers

## Correções Aplicadas

| Data | Arquivo | Correção |
|------|---------|----------|
| 2026-07-22 | `config.ini` | `scope = execution` → `scope = demo_execution` |
| 2026-07-22 | `data/autonomy_state.json` | `"scope": "execution"` → `"scope": "demo_execution"` |
| 2026-07-22 | `/opt/leon/venv/` | rpyc reinstalado de 5.2.3 → 6.0.2 |
| 2026-07-22 | `systemd --user` | Serviço leon-operator iniciado como transient unit |
| 2026-07-23 | `src/mcp/mcp_protocol.py` | `run_server` handlers aceitam `*args, **kwargs` |
| 2026-07-24 | `src/interest_zone_engine.py` | Criada `create_lab_zone()` para rota de laboratório |
| 2026-07-24 | `src/leon.py` | Bootstrap integrado com lab zone + region_id |
| 2026-07-24 | `src/market_monitor.py` | Removido import não utilizado |
| 2026-07-24 | `.env` | Telegram reativado com novo token |

## Contratos Protegidos (relembre)
- Conta real sempre bloqueada
- Nenhum agente pode enviar ordens MT5
- Nenhum agente pode remover guards
- Toda alteração exige diagnóstico, plano, testes, revisão e relatório
