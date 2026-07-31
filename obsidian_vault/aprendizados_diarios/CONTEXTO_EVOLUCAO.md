# Contexto de Evolução — Aprendizados Acumulados

Este arquivo é carregado por todos os agentes ao iniciar uma missão.
Contém padrões, decisões, erros e correções acumulados que evoluem o conhecimento da equipe.

## Como usar
- Leia este arquivo no início de cada missão
- Adicione novos aprendizados ao final do dia em `tarefas/aprendizados_diarios/YYYY-MM-DD.md`
- Apenas padrões recorrentes e decisões estruturais devem ser promovidos para cá

---

## Padrões Identificados

- **Web App**: `web_app/services/` com nomes descritivos (`system_health_service.py`, `web_security_service.py`), `web_app/routes/` organizado por domínio (`auth_routes.py`, `analysis_routes.py`)
- **Web App**: Templates Flask usam exclusivamente `{{ }}` com auto-escaping — sem `|safe` ou `autoescape false`
- **Web App**: CSS design system único em `static/css/style.css` em vez de múltiplos arquivos fragmentados
- **Web App**: `config.py` com classes e constantes tipadas, não YAML/JSON — configuração em Python puro
- **CSS**: Stats-grid responsivo com `auto-fit` + `minmax()` elimina necessidade de media queries fixas
- **CSS**: Variáveis CSS (`--yellow`, `--yellow-bg`) para paleta de cores consistente
- **Ícones**: Unicode em vez de font icons ou imagens para status indicators (✓✗⚠)
- **Segurança**: CSP centralizado em config.py, CSRF via `before_request` global, rate limit login/IP+username
- **Imports sempre com prefixo `src.`**: Todos os módulos devem usar `from src.xxx import Y`. Evitar `from xxx import Y` para módulos dentro de `src/`, pois só funciona quando `PYTHONPATH` inclui `src/` explicitamente.

## Decisões Estruturais

- **Process detection Linux**: Usar `psutil.process_iter()` como método primário, `pgrep -f` como fallback. Substitui PowerShell que falha no Ubuntu 24.04. `psutil` 5.9.8 já está disponível no venv.
- **MT5 health cache TTL 30s**: Cache com `threading.Lock()` e `time.monotonic()` no health check. Evita `mt5.initialize()` + `mt5.shutdown()` a cada requisição HTTP. Redução de ~99.9% das chamadas MT5 no web panel.
- **CSP com `unsafe-inline`**: Content-Security-Policy configurado com `frame-ancestors 'none'`, `form-action 'self'`, `default-src 'self'` + `style-src 'self' 'unsafe-inline'`. Necessário para badges dinâmicos e JS inline. Configurado em `config.py`, não hardcoded.
- **config.py centralizado**: Todas as constantes do web panel (CSP directives, TTLs, debug flags, paths) em `web_app/config.py`. Evita hardcoded em arquivos de rota e serviço.
- **Lazy initialization de MT5**: `mt5_safe` e wrappers MT5 inicializam apenas na primeira chamada real, não no import do módulo. Evita falhas de conexão durante importação e reduz latência em módulos que podem nunca usar MT5.
- **Paginação server-side com links GET (sem JS)**: COUNT query + LIMIT/OFFSET + links de navegação GET. Padrão usado em `analysis_history` e `leon_panel` access-logs.
- **Grid responsivo com `auto-fit` + `minmax()`**: Em vez de media queries fixas, usar `grid-template-columns: repeat(auto-fit, minmax(140px, 1fr))` para stats-grid adaptativo.
- **Ícones unicode para status**: `✓` (online), `✗` (offline), `⚠` (warning) com classes CSS `.status-icon.on/.off/.warn` e cores dinâmicas por estado.
- **rpyc 6.0.2 > rpyc 5.2.3**: Servidor wine MT5 roda rpyc 6.0.2. Cliente venv foi downgrade para 5.2.3 pelo mt5linux. Solução: reinstalar rpyc==6.0.2. mt5linux declara `rpyc==5.2.3` como dependência mas funciona com 6.0.2.
- **systemd --user**: Usuário `leon` não tem sudo. Serviço instalado como `systemd-run --user --unit=leon-operator` (transient, não persistente após reboot). Alternativa: usar crontab @reboot ou solicitar configuração de sudo NOPASSWD.
- **Autonomy scope**: Config.ini tinha `scope = execution`, código exige `scope = demo_execution` ou `learning_and_demo`. Corrigido em config.ini e `autonomy_state.json`.
- **Telegram via `.env`**: credenciais lidas prioritariamente de `/opt/leon/config/.env`, com symlink em `/opt/leon/app/.env`; `config.ini` permanece apenas como fallback.
- Usar obsidian-headless (CLI oficial) em vez de app GUI (servidor headless)
- Vault Obsidian como complemento, não substituto, do sistema de aprendizado diário
- Sincronização bidirecional entre `obsidian_vault/aprendizados_diarios/` e `tarefas/aprendizados_diarios/`
- Script de integração em `scripts/sync_obsidian_vault.sh` para manter ambos atualizados
- **MCPs em `src/mcp/`** — diretório dedicado, sem poluir src/ raiz
- **Wrapper `mt5_safe.py`**: interface canônica somente leitura para os MCPs, bloqueando funções de ordem. `_mt5_safe.py` permanece apenas como referência histórica.
- **MCPs orquestram, não implementam** — Backtest MCP chama engines existentes
- **`opencode.json` no projeto** para registrar MCPs sem modificar config global

## Erros Recorrentes

- **Conexão MT5 falha**: `ValueError: invalid message type: 18` — incompatibilidade rpyc 5.2.3 (cliente) vs 6.0.2 (servidor wine).
- **Autonomy scope incorreto**: Config `scope = execution` bloqueia execução demo. Código espera `demo_execution` ou `learning_and_demo`.
- **State file precedence**: `autonomy_state.json` sobrescreve config.ini para scope. Mesmo alterando config.ini, state file persistia valor antigo.
- **sudo não disponível**: Usuário `leon` não está no sudoers. Serviços systemd não podem ser instalados como system service.
- **PowerShell no Linux**: `subprocess.run(["powershell", ...])` é Windows-only. Falha silenciosamente no Ubuntu 24.04. Verificador: sempre usar `psutil` ou `pgrep` para detecção de processos no Linux.
- **Navegação duplicada**: Templates com `{% extends "base.html" %}` conflitantes geram menu duplicado. Verificador: inspecionar se há mais de um block de navigation/sidebar.
- **Código morto**: Funções duplicadas ou cópias de rotas acumulam durante desenvolvimento. Verificador: ao modificar um arquivo, verificar se há cópias da mesma lógica em outros arquivos.
- **Import sem prefixo `src.`**: `from study_engine import ...` em vez de `from src.study_engine import ...`. Funciona apenas com PYTHONPATH incluindo `src/`, falha em ambiente de teste padrão. Verificador: ao criar ou modificar módulos em `src/`, usar sempre `from src.xxx import Y`.
- **`sys.exit()` em testes**: `test_leon_brain.py` usa `sys.exit(0)` no final do módulo, causando `INTERNALERROR: SystemExit` no pytest. Impede execução em lote da suíte. Verificador: em testes, usar `pytest.fail()` ou `raise AssertionError`; nunca `sys.exit()`.
- **Hardcoded absolute paths Linux**: Apesar de Windows paths (`C:/XAU_ELITE_AI/`) terem sido removidos, ~20+ arquivos ainda usam `/opt/leon/app/data/...` hardcoded em vez do helper `paths.py`. Verificador: usar `from paths import DATA_DIR, LOGS_DIR, REPORTS_DIR` em vez de caminhos absolutos.
- **Mocks de teste incompletos**: Quando novas chaves de configuração são adicionadas ao código, os mocks de teste correspondentes não são atualizados. Como os imports quebrados mascaram essas falhas, elas ficam invisíveis até que a cadeia de import seja corrigida. Verificador: ao adicionar nova chave em config no código, atualizar TODOS os mocks que mockam aquela config.

## Correções Aplicadas (Histórico)

| Data | Arquivo | Correção |
|------|---------|----------|
| 2026-07-22 | `config.ini` | `scope = execution` → `scope = demo_execution` |
| 2026-07-22 | `data/autonomy_state.json` | `"scope": "execution"` → `"scope": "demo_execution"` |
| 2026-07-22 | `/opt/leon/venv/` | rpyc reinstalado de 5.2.3 → 6.0.2 |
| 2026-07-22 | `systemd --user` | Serviço leon-operator iniciado como transient unit |
| 2026-07-23 | `src/mcp/run_server.py` | `*args, **kwargs` adicionado nos `__init__` dos 4 handlers |
| 2026-07-27 | `web_app/services/system_health_service.py` | `_process_running()`: PowerShell → `psutil` + `pgrep` |
| 2026-07-27 | `web_app/services/system_health_service.py` | `_mt5_status()`: cache TTL 30s com `threading.Lock()` |
| 2026-07-27 | `web_app/services/system_health_service.py` | `mt5_safe` lazy init |
| 2026-07-27 | `config/leon_config.py` | Hardcoded Windows paths removidos |
| 2026-07-27 | `web_app/templates/leon_panel.html` | Menu duplicado removido + busca/filtro + paginação + shadow_trades |
| 2026-07-27 | `web_app/routes/leon_routes.py` | Código morto `access_logs_page` removido |
| 2026-07-27 | `web_app/routes/analysis_routes.py` | Paginação LIMIT/OFFSET + COUNT |
| 2026-07-27 | `web_app/static/css/style.css` | Stats-grid responsivo + `--yellow` + transições + scrollbar + ícones |
| 2026-07-27 | `web_app/config.py` | CSP directives centralizadas |
| 2026-07-28 | `src/operational_study_engine.py` | `from study_engine import ...` → `from src.study_engine import ...` (import sem prefixo quebrava a cadeia) |
| 2026-07-28 | `tests/test_mt5_order_executor.py` | Adicionado `test_operational_study_engine_importa` (teste de regressão para o import) |

## Contratos Protegidos (relembre)
- Conta real sempre bloqueada
- Nenhum agente pode enviar ordens MT5
- Nenhum agente pode remover guards
- Toda alteração exige diagnóstico, plano, testes, revisão e relatório
- 2026-07-28 | TEST-000001 | WIN_TP1 COMPRA Gold_Spot | SMC=BULLISH Elliott=ABC_RANGE Brain=65 | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
- 2026-07-30 | PREOP-000116 | WIN_TP1 ? None | SMC=? Elliott=? Brain=? | Confluencia valida, registrar padrao
