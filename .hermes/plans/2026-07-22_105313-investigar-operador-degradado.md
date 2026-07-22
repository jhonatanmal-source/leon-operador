# Investigação do operador degradado — plano somente leitura

> **Para Hermes:** executar somente diagnóstico estático e leitura de artefatos. Não iniciar MT5, não importar/chamar rotinas que conectem ao MT5, não enviar mensagens/ordens, não alterar configurações, estratégia, código, serviços, lock ou handoff.

**Objetivo:** produzir uma causa raiz verificável para a degradação do operador LEON e um pacote de correção posterior, sem executar qualquer operação de mercado nem mutação no ambiente.

**Arquitetura sob investigação:** o ciclo em `src/leon_operator.py` agenda coleta, análise, execução demo e telemetria. O coletor escreve preços/candles por meio dos loggers; `src/operator_status.py` e `src/operation_readiness.py` leem o diretório canônico `data/`; o watchdog e a aplicação web expõem a saúde. A investigação deve reconciliar produtor, consumidor e supervisão do processo.

**Restrições invioláveis:**
- Não executar `src/leon_operator.py`, `src/leon.py`, `src/collector_operator.py`, `src/mt5_*`, `src/market_session_guard.py` nem scripts/serviços MT5.
- Não consultar a rota/painel que aciona `web_app/services/system_health_service.py::build_system_health()`: ela chama `_mt5_status()`, que faz `mt5.initialize()` e `mt5.shutdown()`.
- Não executar comandos `systemctl start|stop|restart`, não alterar `config.ini`, não editar `tarefas/agent_lock.json` nem `tarefas/handoff_atual.md`.
- Não enviar Telegram, não conceder/revogar autonomia e não executar testes que possam acionar infraestrutura externa. A coleta de evidência deve ser feita com leitura de arquivos e análise estática.

## Evidência inicial já disponível

1. `src/price_logger.py:12`, `src/candle_logger.py:18`, `src/signal_logger.py:17` e `src/trade_plan_memory.py:8` gravam no caminho relativo legado `C:/XAU_ELITE_AI/data/...`.
2. `src/operator_status.py:15-17` e `src/leon_operator.py:71-81` definem o diretório canônico como `<raiz>/data`, isto é, `/opt/leon/app/data`.
3. O histórico de diagnóstico aponta que os quatro artefatos canônicos esperados estavam ausentes enquanto os arquivos no caminho legado recebiam atualizações. Consequência: `operator_status` informa `SEM DADOS`; `operation_readiness` bloqueia/coleta motivos em `src/operation_readiness.py:27-46`.
4. O operador possui heartbeat canônico em `data/operator_heartbeat.json`, produzido por `src/leon_operator.py:148-164` e atualizado no loop `1116-1302`. A ausência ou idade alta desse arquivo deve ser tratada como evidência de processo não supervisionado/inativo.
5. A configuração atual contém `demo_execution_enabled = true` e `AUTONOMY.enabled = true` (`config.ini:29-51`). Isso aumenta a exigência de isolamento: a investigação não pode executar o entrypoint nem qualquer caminho que importe/ative coleta ou execução.
6. O repositório possui alterações locais pré-existentes. Esta missão não deve interpretá-las como suas nem modificá-las.

## Arquivos envolvidos

### Produtores de dados
- `src/collector_operator.py:16-101` — coleta de tick/candle; contém chamadas MT5 e fica fora de execução nesta missão.
- `src/price_logger.py` — grava `price_history.csv` no caminho legado.
- `src/candle_logger.py` — grava `candle_history.csv` no caminho legado.
- `src/signal_logger.py` — grava `signals.csv` no caminho legado.
- `src/trade_plan_memory.py` — grava `trade_plan_memory.csv` no caminho legado.
- `src/leon_operator.py:71-81, 148-164, 1116-1302` — ciclo, arquivos de estado e heartbeat.

### Consumidores, bloqueio e observabilidade
- `src/operator_status.py:251-300` — lê `data/price_history.csv` e `data/candle_history.csv`; classifica `SEM DADOS`, `DADOS ANTIGOS` ou `OK`.
- `src/operation_readiness.py:9-75` — transforma status do coletor/setup/pré-operação em prontidão.
- `src/system_watchdog_agent.py:172-252` — lê e valida `data/operator_heartbeat.json`; correlaciona erros e últimos sucessos.
- `web_app/services/system_health_service.py:186-230, 254-312` — agrega saúde, mas seu caminho MT5 não é seguro para esta missão somente leitura.
- `config.ini:29-51` — cadência, sessão de mercado, demo e autonomia; apenas leitura.

### Testes e artefatos de coordenação
- `tests/test_leon_operator_resilience.py` — contratos de configuração, isolamento de falhas e escrita atômica do estado.
- `tests/test_pre_operation_pipeline_consistency.py` — contrato de identidade de ciclo/pré-operação.
- `tests/test_web_active_errors.py` — regra de ocultar erros históricos após sucesso.
- `tests/test_market_session_guard.py` — testes com fake MT5; não executar nesta fase.
- `tarefas/agent_lock.json` — está livre no momento da leitura; não reservar nesta fase.
- `tarefas/handoff_atual.md` — contexto da revisão anterior; somente leitura.

## Distribuição de tarefas

### OpenCode — Triagem e observabilidade (leitura apenas)

**Responsável:** OpenCode, usando o papel `leon-observability-engineer`.

**Objetivo:** estabelecer a linha do tempo operacional e demonstrar, por artefatos estáticos/arquivos de estado, se a degradação decorre de processo ausente, heartbeat expirado, dados no local errado ou ambos.

**Entradas permitidas:**
- `data/operator_heartbeat.json`, `data/collector_state.txt`, `data/analysis_state.txt`, `data/session_status.json` se existirem;
- `logs/leon_log.txt`, `logs/errors.txt`, `logs/operator_runtime_error.log`, `logs/errors_fallback.txt`;
- `reports/setup_audit_2026-07-22.{json,txt}`;
- fontes de observabilidade listadas acima.

**Procedimento:**
1. Ler metadados/timestamps dos artefatos, sem executar programas do projeto.
2. Montar uma linha do tempo: último heartbeat, última coleta registrada, última análise programada, último erro crítico e último relatório de auditoria.
3. Verificar se os IDs de ciclo/análise nos estados e logs podem correlacionar uma coleta com a análise correspondente.
4. Comparar, apenas por presença e data de modificação, `/opt/leon/app/data/` contra `/opt/leon/app/C:/XAU_ELITE_AI/data/` para os quatro CSVs.
5. Entregar relatório factual com tabela `evidência | timestamp | fonte | interpretação | confiança`, separando fato de hipótese.

**Proibições explícitas no prompt do agente:** não usar rota web, `python -m`, entrypoints, `systemctl`, MT5, Telegram, comandos de escrita ou alterações em lock/handoff.

**Saída esperada:** relatório de diagnóstico sem alterações, contendo a causa primária e causas contributivas com evidência reprodutível.

### Codex — Análise de contrato e plano de correção/testes (leitura apenas)

**Responsável:** Codex, em modo revisão/análise; não usar flags de escrita automática.

**Objetivo:** derivar a menor correção futura que unifique o caminho de persistência e torne o estado degradado observável sem acionar MT5.

**Entradas permitidas:** os quatro loggers, `collector_operator.py`, `operator_status.py`, `operation_readiness.py`, `system_watchdog_agent.py`, `leon_operator.py`, `system_health_service.py` e os testes listados.

**Procedimento:**
1. Produzir um grafo produtor → arquivo → consumidor para `price_history.csv`, `candle_history.csv`, `signals.csv` e `trade_plan_memory.csv`.
2. Identificar uma única fonte canônica de `DATA_DIR` já adotada pelo projeto e os pontos mínimos a refatorar, sem propor mudança de gates/estratégia.
3. Projetar testes unitários isolados por `tmp_path`/`TemporaryDirectory` que provem: (a) loggers escrevem somente no diretório canônico; (b) `operator_status` reconhece esses dados; (c) heartbeat ausente/antigo vira estado degradado; (d) health web pode informar indisponibilidade sem chamar MT5 quando em modo de diagnóstico.
4. Avaliar se `system_health_service.py` necessita separação explícita entre health local baseado em arquivos e health de conectividade MT5; registrar isso como proposta, não implementar.
5. Entregar somente uma especificação de patch: caminhos, funções, contratos de teste e riscos de migração/compatibilidade de CSV.

**Proibições explícitas no prompt do agente:** não executar testes, não iniciar/importar MT5, não iniciar serviços, não alterar arquivos, não executar comandos de ordem/autonomia/Telegram.

**Saída esperada:** proposta de patch mínima e lista de testes, preservando integralmente os guards e a estratégia.

## Sequência de execução

### Etapa 1 — Congelamento de escopo
1. Registrar no relatório que esta é uma missão de diagnóstico e que código/configuração não serão alterados.
2. Ler `tarefas/agent_lock.json` e `tarefas/handoff_atual.md`; manter o lock livre.
3. Reafirmar em cada prompt de subagente as proibições de MT5, ordens, Telegram, autonomia e escrita.

### Etapa 2 — Diagnóstico independente em paralelo
1. OpenCode executa a tarefa de observabilidade exclusivamente por leitura.
2. Codex executa a análise estática do contrato de armazenamento e testes exclusivamente por leitura.
3. Nenhum agente roda comandos do projeto, serviços, testes ou interface web.

### Etapa 3 — Reconciliação por Hermes
1. Cruzar a linha do tempo de OpenCode com o grafo de dados de Codex.
2. Classificar a causa como confirmada somente se houver evidência dos dois lados: produtor em caminho legado e consumidor no caminho canônico, ou heartbeat/processo sem atualização.
3. Registrar causas alternativas não confirmadas (por exemplo, sessão de corretora, falha MT5, permissões) sem investigá-las por acesso ao MT5.
4. Produzir recomendação de correção posterior com escopo limitado a persistência, supervisão e health check local.

### Etapa 4 — Critérios para uma missão posterior de correção
Somente após autorização humana explícita e nova missão de escrita:
1. Reservar arquivos no lock e criar checkpoint.
2. Corrigir a responsabilidade do `DATA_DIR` em um único módulo/configuração compartilhada; não duplicar caminhos.
3. Migrar/compatibilizar dados legados de forma explícita e auditável, sem apagar dados.
4. Acrescentar testes de caminho canônico, status do coletor, heartbeat e health local sem MT5.
5. Revisar o diff, rodar apenas testes isolados autorizados e manter execução real bloqueada.

## Critérios de aceitação desta missão

- Nenhuma chamada ao MT5, ordem, Telegram, autonomia, serviço ou estratégia.
- Nenhuma alteração fora deste arquivo de plano.
- Duas entregas independentes: evidência operacional (OpenCode) e especificação de correção/testes (Codex).
- Causa raiz apresentada com arquivos, linhas, timestamps e nível de confiança.
- Plano posterior não reduz guards, não libera conta real e não muda regras de trading.

## Riscos e perguntas abertas

- O diretório `C:/XAU_ELITE_AI/` dentro do workspace pode ser uma compatibilidade legada criada no Linux, e não um volume Windows real; confirmar por leitura de metadados, sem escrever.
- A existência de heartbeat antigo não distingue sozinho crash, serviço não instalado ou pausa de mercado; a linha do tempo deve usar estados/logs para diferenciar.
- `system_health_service.py` contém chamada MT5 em sua agregação; qualquer investigação futura via painel deve primeiro receber um caminho de diagnóstico estritamente file-backed.
- Alterações locais não comitadas já existem. Uma futura correção deve evitar sobrepor trabalho prévio e só pode começar após lock/handoff atualizado.
