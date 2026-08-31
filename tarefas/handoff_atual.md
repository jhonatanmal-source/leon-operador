# Handoff Atual

## 🟢 CONCLUÍDA: MISSION-20260830-AUTO-LEARNING — Mecanismo de Aprendizado Automático
- **Categoria**: IA — Captura automática de aprendizados do agente
- **Estado**: ✅ IMPLEMENTADA + TESTADA + DOCUMENTADA + APROVADA
- **O que foi feito**: Mecanismo que salva automaticamente o que o agente aprende conforme o mercado está agindo, sem exigir registro manual no final de cada missão.
- **Arquivos criados**:
  - `src/learning_capture.py` (NOVO, 325 linhas) — Módulo Python de captura automática
  - `docs/automatic_learning_mechanism.md` (NOVO, 231 linhas) — Documentação completa
- **Funcionalidades**:
  - 5 checkpoints automáticos: TRIAGEM, DIAGNÓSTICO, PLANO, IMPLEMENTATION, TESTES
  - Filtro de segurança com 66 palavras-chave sensíveis (TP, SL, conta real, tokens, balance, risk, RR, etc.)
  - Promoção inteligente para CONTEXTO_EVOLUCAO.md (respeita marcador CURADO_MANUALMENTE)
  - Atualização automática do INDICE.md
  - Idempotência (evita duplicatas)
- **Testes**: End-to-end completo, filtro de sensibilidade validado, integração com sistema existente
- **Segurança**: Conta real, TP, SL, tokens, strategy details NUNCA salvos
- **Próximos passos**: Integrar chamadas automáticas no leon-engineering-director.md; criar testes unitários em tests/test_learning_capture.py; expandir para mais checkpoints
- **Pendência de commit**: Arquivos novos não commitados (aguardando autorização)

---

## 🔒 AUDITORIA DE BRECHAS (2026-08-25) — INPUT PARA MISSÃO EM ANDAMENTO
> Levantamento somente leitura feito pelo agente de revisão para subsidiar a missão do agente ativo. NADA foi alterado.

### 🔴 CRÍTICAS
1. **`web_app/database/mt5_credentials.json` está `root:root` (600) e o serviço web roda como `leon`** — o service NÃO consegue ler nem escrever o store de credenciais MT5. Agravante: `_read_store()` (`mt5_credential_service.py:88-97`) **mascara o erro** retornando `{}` silenciosamente (`except OSError: return {}`) → feature de credenciais parece funcionar mas opera vazia/falha oculta. Mesma classe do incidente `web_access.log` de hoje (root vs leon). **Corrigir**: `chown leon:leon` no arquivo + substituir masking silencioso por log de erro explícito + verificação de permissão no startup.
2. **Telegram: `ALLOWED_CHAT_IDS = []` (`telegram_commands_mcp.py:75`) = qualquer chat que descubra o token comanda o bot**, incluindo `/go` e `/autonomy on` (ativam autonomia de execução DEMO!). Pré-requisito bloqueante da Fase 1 da missão TELEGRAM-MT5-CONTAS; recomenda-se aplicar allowlist também a `/go`, `/autonomy`, `/memory` e `/backtest`.

### 🟠 ALTAS
3. **HTTP aberto na internet sem redirect para HTTPS + `SESSION_COOKIE_SECURE` default false** (`web_app/config.py:19`) — login e cookie de sessão podem trafegar em texto claro via porta 80. Corrigir: redirect 80→443 no openresty (exceto futura rota ACME) + `SESSION_COOKIE_SECURE=true`.
4. **Certificado self-signed**: usuário precisa aceitar warning manualmente (risco de MITM consciente). Plano de médio prazo: domínio dedicado + Let's Encrypt.

### 🟡 MÉDIAS
5. **rpyc classic na 18812 sem autenticação** — qualquer processo LOCAL obtém API MT5 completa (inclusive envio de ordens). Mitigado pelo bind em 127.0.0.1 (validado), mas recomenda-se credencial rpyc (`rpyc.core.auth`) ou configuração restritiva como defesa em profundidade.
6. **`SECRET_KEY` com fallback aleatório por processo** (`web_app/config.py:16`) — se `.env` perder a chave, todas as sessões invalidam a cada restart e múltiplos workers divergem. Landmine; hoje `.env` TEM a chave (ok).
7. **Aviso permanente no template de login** ("Admin inicial: verifique o `.env` e troque a senha") informa a atacantes que pode haver senha padrão. Remover após confirmação de troca de senha (relacionado à pendência #1 de rotação).

### ✅ VERIFICADO SEM BRECHA
CSRF global no `before_request`; cookie HttpOnly+SameSite=Lax; rate limit de login (15 min); senhas com werkzeug hash; `.master_key` com `r--------` leon; `.env` (600, fora do git); UFW default-deny; portas sensíveis (5000, 18812, MCPs) apenas em loopback; store com chmod 600 (intenção correta, owner errado — item 1).

---

## 🚨 URGENTE — AGUARDANDO APROVAÇÃO: MISSION-20260825-WEB-RPYC-TIMEOUT
- **Severidade ALTA — indisponibilidade intermitente do painel web remoto** (reproduzida e diagnosticada em 2026-08-25).
- **Causa raiz 1 (estrutural)**: chamadas rpyc/MT5 **sem timeout** no caminho de render de TODA página: `inject_current_user` (`web_app/app.py:48`) → `get_mt5_account_summary` (`system_health_service.py:540`) → `mt5.initialize` via gateway Wine porta 18812. Quando o gateway trava/lenta, as **4 threads do waitress bloqueiam indefinidamente** → app inteiro em 504/timeout. Evidência: py-spy dump com as 4 threads presas em `rpyc sync_request`, `Task queue depth` 12+, sockets CLOSE-WAIT.
- **Causa raiz 2**: `logs/web_access.log` era `root` (serviço roda como `leon`) → PermissionError a cada login. ✅ Mitigado com chown em 2026-08-25.
- **Infra já corrigida nesta data** (fora desta missão): HTTPS habilitado no openresty (bloco 443 + cert self-signed em `/etc/ssl/leon/`, config em `tarefas/missoes/.../conf.d/users/leon-web.conf` do icontainer). Porta 443 validada acessível externamente via check-host.net (5 nós).
- **Plano (A+B+C)**: timeout rpyc (~10–15s) + cache TTL do status MT5 (sem chamada MT5 por render) + health assíncrono no painel. Detalhes, critérios de aceitação e guards em `tarefas/missoes/MISSION-20260825-WEB-RPYC-TIMEOUT.md`.
- **Guards**: somente leitura MT5; estratégia/risco/TP/SL/execução intocados; REAL bloqueada; gateway Wine não é tocado.
- **⚠️ Risco de não agir**: qualquer travamento do gateway MT5 (incidente `IPC send failed` de 24/08 já demonstrou recorrência) derruba o acesso remoto ao painel — inclusive supervisão humana durante operações demo.
- **Próxima ação**: usuário autoriza → Engineering Director convoca equipe (Senior Software Engineer implementação + QA testes + Reviewer) → executa com lock próprio.

---

## 🟡 AGUARDANDO APROVAÇÃO: MISSION-20260825-TELEGRAM-MT5-CONTAS
- **Origem**: pedido do usuário — "montar um plano para adicionar ao Telegram painel para adicionar contas ao MT5".
- **Estado**: plano completo criado; **nada implementado** — aguardando aprovação.
- **Especificação completa**: `tarefas/missoes/MISSION-20260825-TELEGRAM-MT5-CONTAS.md`.
- **Decisões do usuário (2026-08-25)**: escopo **MULTI-CONTA** (alinhado à Fase 0/1 do plano FTMO) e senha via **fluxo em 2 passos** (senha nunca em comando único).
- **Resumo em 3 fases**:
  - **Fase 1**: allowlist de admins no Telegram (`LEON_TELEGRAM_ADMIN_CHAT_IDS` em `.env`) — pré-requisito de segurança, hoje `ALLOWED_CHAT_IDS=[]` permite qualquer chat com o token.
  - **Fase 2**: evolução multi-conta de `mt5_credential_service` com migração não-destrutiva do store atual (conta existente vira a ativa); web `/mt5-account` segue funcionando.
  - **Fase 3**: comandos `/conta` (listar/add 2 passos/ativar/testar/remover com confirmação), reusando Fernet + guards existentes.
- **Guards**: REAL bloqueada em código; nenhuma ordem enviada; senha nunca ecoada/logada; gateway MT5 intocado.
- **Próxima ação**: usuário aprova → Engineering Director convoca equipe para implementar fase a fase com testes entre cada.

---

## 🟣 PLANO ESTRATÉGICO — AGUARDANDO APROVAÇÃO: MISSION-20260825-FTMO-PLAN
- **Origem**: pedido do usuário — "planejamento para rodarmos nosso agente na FTMO".
- **Estado**: plano completo criado e salvo; **NADA executado** — aguardando aprovação e informações da conta.
- **Especificação completa**: `tarefas/missoes/MISSION-20260825-FTMO-PLAN.md`.
- **Resumo em 5 fases**:
  - **Fase 0**: mapear conta FTMO (tipo Normal/Swing, tamanho, fase alvo) → documentar regras exatas em `docs/ftmo_rules.md`
  - **Fase 1**: conectar MT5 da FTMO via painel de credenciais (⚠️ depende de MISSION-20260825-MT5-CREDENCIAIS-WEB)
  - **Fase 2**: novo `src/ftmo_guard.py` — perda diária vs limite FTMO, drawdown total vs 10%, contador de dias mínimos, kill switch com buffer (pausa em 6% drawdown / 2% dia), card FTMO no painel
  - **Fase 3**: operação no Challenge (DEMO) com relatório diário no Telegram
  - **Fase 4**: Verification → funded é SEMPRE decisão humana manual; agentes não liberam conta real
- **Alinhamentos já existentes** (bom news): News Shield ativo (regra FTMO de notícias ✓), risco interno 0.5%/trade + perda diária 2% (mais conservador que os 5% FTMO), max_open_positions 2.
- **Decisão do usuário (2026-08-25)**: **AUTOMAÇÃO TOTAL** das entradas no Challenge/Verification (contas DEMO) — sem aprovação manual por operação; supervisão via painel + Telegram. Exige kill switch automático rigoroso na Fase 2 (pausa dia em 2%, pausa geral em 6% drawdown). **Conta FUNDED = REAL permanece bloqueada para agentes** — liberação futura é decisão manual e formal do usuário, fora da autoridade de agentes.
- **Guards inegociáveis**: estratégia intocada (FTMO adapta guards, não estratégia); funded bloqueada para agentes; parâmetros de risco só mudam com aprovação explícita.
- **AJUSTE APROVADO (2026-08-26)**: usuário NÃO vai definir tamanho de conta manualmente — haverá VÁRIAS contas FTMO de tamanhos diferentes. **Fase 0 muda de "usuário informa tamanho" para "LEON detecta automaticamente ao conectar"**:
  - Ao conectar, LEON lê `mt5.account_info()` (padrão já usado em `mt5_monitor.py`): `login`, `server`, `trade_mode`, `currency`, `balance`.
  - Limites FTMO são PERCENTUAIS (5% dia, 10% total) → independem do tamanho. Guard calcula o valor em dinheiro dinamicamente a partir do `balance` inicial detectado. Funciona para 10k/25k/100k/qualquer tamanho sem config manual.
  - No primeiro connect de cada `login`, grava snapshot do `balance` inicial como baseline de drawdown (ancorado, não usa `equity` que oscila). Cada conta nova gera perfil próprio automaticamente — sem intervenção manual.
  - `trade_mode` continua sendo o guard DEMO vs REAL — isso não muda (funded real permanece bloqueada).
  - **Pendência de infraestrutura**: `tarefas/missoes/MISSION-20260825-FTMO-PLAN.md` está `root:root` (0644) — usuário `leon` sem permissão de escrita, edição da Fase 0 no arquivo original bloqueada. Decisão registrada aqui no handoff até correção de owner ou execução via usuário com privilégio. Não afeta a decisão nem a implementação futura.
- **✅ APROVADO pelo usuário (2026-08-26) e Fase 2 IMPLEMENTADA + TESTADA (sem commit)**:
  - `src/ftmo_guard.py` (NOVO): `avaliar_conformidade_ftmo()` (cálculo puro, testável sem MT5) + `registrar_perfil_conta()` (baseline por login em `data/ftmo_accounts.json`, grava `balance` inicial no primeiro connect e preserva depois) + `avaliar_guard_ftmo()` (leitura real MT5) + `resumo_ftmo()`.
  - Limites percentuais (5% dia / 10% drawdown, buffer interno 2%/6%) calculados dinamicamente sobre o `baseline_balance` detectado — funciona para qualquer tamanho de conta sem config manual.
  - `config.ini` + `config.ini.example`: nova seção `[FTMO]` (`enabled=false` por padrão, seguro).
  - Integrado em `src/mt5_order_executor.py` (`executar_ordem_mt5_pre_operacao`) logo após o guard de perda diária existente — guard ADICIONAL, não substitui nada; quando desativado retorna `FTMO_GUARD_DISABLED` e não bloqueia nada (validado).
  - **Testes**: `tests/test_ftmo_guard.py` NOVO (17 testes: cálculo puro, multi-tamanho de conta, baseline por login, violações reais FTMO vs buffer interno, configs). Suíte completa: **460/460 passed** (`--ignore=tests/test_leon_brain.py`).
  - **Segurança validada**: REAL/FUNDED continua bloqueada por outros guards; `ftmo_guard` só classifica (`is_demo` via `trade_mode`), nunca libera nada, nunca envia ordem.
  - **⚠️ Pendência de infraestrutura**: `tarefas/missoes/MISSION-20260825-FTMO-PLAN.md` é `root:root` (0644) — usuário `leon` sem permissão de escrita nesse arquivo específico (outros da pasta têm o mesmo problema: `MISSION-20260825-MT5-CREDENCIAIS-WEB.md`, `MISSION-20260825-CENTRAL-VIRTUAL-VIVA.md`). Decisão da Fase 0 e conclusão da Fase 2 registradas aqui no handoff em vez do arquivo da missão. Corrigir owner (`chown leon:leon`) quando possível.
  - **Próxima ação**: aguardar autorização para commit desta Fase 2; depois seguir para Fase 3 (card FTMO no painel + relatório diário Telegram) e cadastro real das credenciais FTMO via `/mt5-account` (pré-requisito já concluído na missão de credenciais).

---

## 🟡 EM AJUSTE — AGUARDANDO APROVAÇÃO: MISSION-20260825-CENTRAL-VIRTUAL-VIVA
- **Origem**: pedido do usuário — "painel web mais melhorias, quero painel virtual mais vivo, quero tudo planejado".
- **Estado**: plano completo criado; usuário pediu **ajustes antes de aprovar** — refinamento iterativo em andamento.
- **Especificação completa**: `tarefas/missoes/MISSION-20260825-CENTRAL-VIRTUAL-VIVA.md` (diagnóstico com evidências, 3 fases, arquivos previstos, guards, critérios de aceitação + seção aberta "Ajustes pendentes" para registrarmos cada rodada de ajuste).
- **Resumo do plano**:
  - **Fase 1 (núcleo)**: endpoint `/central-virtual/api/snapshot` (JSON, autenticado) + cache TTL 15s + polling adaptativo no JS (pausa com aba oculta) → tela atualiza sozinha sem F5.
  - **Fase 2**: feed de atividade real do operador (últimas 5 ações), linha de mercado (preço/fase/tendência do contexto salvo), destaques visuais de transição de status.
  - **Fase 3**: polimento (fade nas mudanças, reduced-motion, fallback gracioso).
- **Diagnóstico-chave**: a Central Virtual é rica mas estática — snapshot só no render server-side, zero API, zero polling (`central_virtual.js` sem `fetch()`).
- **Guards**: página READ ONLY; nenhuma chamada MT5 nova; operacional/risco/TP/SL intocados.
- **Próxima ação**: usuário indica ajustes → atualizamos o plano na seção "Ajustes pendentes" da missão → nova rodada até aprovação.

---

## 🔴 PRIORIDADE MÁXIMA — AGUARDANDO ORDEM DE EXECUÇÃO: MISSION-20260825-MT5-CREDENCIAIS-WEB
- **✅ CONCLUÍDA E COMMITADA (2026-08-25, commit `3da5a4f`)**: página admin-only `/mt5-account` no painel web para gerenciar credenciais MT5 (login/servidor/senha criptografados com Fernet + chave mestra `/opt/leon/.master_key`), botão "Testar conexão" somente leitura, guard REAL duplo (salvamento só DEMO + teste recusa `trade_mode REAL`), senha nunca exposta. 27 testes novos; suíte 443/443 passed. Commit autorizado pelo usuário.
- **Próximo passo operacional**: cadastrar as credenciais da conta FTMO Challenge via painel (pré-requisito da Fase 1 do plano FTMO abaixo). Se o erro "login/senha inválido" persistir após cadastro via painel, validar sessão wine/rpyc (restart manual de `start-rpyc-server.sh` + `run-mt5-headless`).

---

## 🎯 Última Missão Concluída: MISSION-20260824-PROMOCAO-ZONAS-LAB (bloqueio B2)
- **Estado**: ✅ IMPLEMENTADA + TESTADA (416/416 passed, 13 testes novos) — **sem commit, sem restart do operador** (aguardando autorização).
- **O que resolve**: bloqueio B2 do diagnóstico de 21/08 — zonas LAB nasciam `AGUARDANDO_ESTRUTURA` e nunca eram promovidas a `CONFIRMADA` (nenhum processo alimentava evidência ao `monitor_zone`) → execução demo LAB permanentemente bloqueada (`REGION_NOT_CONFIRMED`).
- **Mecanismo**: novo `src/lab_zone_monitor.py` roda no ciclo de estudo contínuo do operador; agrupa zonas LAB pendentes por símbolo (**1 leitura MT5 por símbolo/ciclo**, não por zona); evidência real via `analyze_smc_context` (M15) + `_micro_trigger` (M5, sweep+reclaim+displacement); promoção EXCLUSIVAMENTE via `monitor_zone` (cadeia completa liquidez→estrutura→gatilho, igual produção); `structural_confirmations` gravadas só após promoção real, com eventos detectados. Hook em `leon_operator.py` com log `OPERATOR | zonas LAB monitoradas: ...`.
- **Escopo consciente**: as **1509 zonas LAB legadas `CONFIRMADA`** (fabricadas antes da correção de 18/08) ficam FORA do monitor — reprocessá-las custaria 1509 leituras MT5/ciclo e as expiraria em massa por idade. Retroatividade = missão dedicada futura se necessário.
- **⚠️ Bloqueio de infraestrutura (PENDENTE DO USUÁRIO)**: MT5 indisponível durante a missão — `mt5.initialize()` → `False`, `(-10001, 'IPC send failed')`. Porta 18812 abre mas IPC falha. Suspeita: duas sessões wineserver simultâneas dessincronizadas (rpyc 20:08 vs terminal64 21:00). Restart exige ação manual fora do workspace (política de permissões nega `/opt/leon/scripts/` a agentes): rodar `start-rpyc-server.sh` → `run-mt5-headless` e validar com `python -c "import mt5_safe as mt5; print(mt5.initialize())"`. Validação end-to-end da missão depende disso.
- **Comportamento seguro validado**: com MT5 fora, monitor faz skip gracioso (`MT5_INITIALIZE_FAILED`), zero mutação de estado, arquivo real intacto (validado contra cópia com md5).
- **Arquivos**: `src/lab_zone_monitor.py` (NOVO), `src/leon_operator.py` (+19 linhas: import + hook), `tests/test_lab_zone_monitor.py` (NOVO, 13 testes), `tarefas/missoes/MISSION-20260824-PROMOCAO-ZONAS-LAB.md`.
- **Próximos passos**: (1) usuário restaura MT5 manualmente; (2) autorizar commit desta missão + das alterações pendentes de 21/08; (3) reiniciar operador para carregar o hook; (4) observar logs `zonas LAB monitoradas` nas 62 zonas legítimas.

## 🛠️ Backlog de Melhorias de Código (análise 2026-08-18 — 9 missões pequenas)

Origem: auditoria de código somente leitura em `src/` (arquivos grandes: `leon_panel.py`, `leon_operator.py`, `interest_zone_engine.py`, `mt5_order_executor.py`, `telegram_commands_mcp.py`, `leon.py`, `pre_operation_engine.py`). Dividido em missões pequenas e independentes para não consumir muito crédito de uma vez. Ordem sugerida: risco crescente. Nenhuma mistura de estratégia/risco/MT5 real. Executar uma por vez, com testes (suíte completa `--ignore=tests/test_leon_brain.py`) e aprovação entre cada.

- [x] **Missão 1 — Bugs triviais de 1 linha** ✅ CONCLUÍDA + COMMITADA (`1a31848` + lock `e88d595`): typo `kilzone_name` → `killzone_name` corrigido em `interest_zone_engine.py:1386` (consistente com as outras 2 ocorrências do arquivo). Import duplicado de `obter_status_operadores` padronizado em `leon_operator.py` — removidos os 2 imports locais `from operator_status import ...` (sem prefixo `src.`, linhas 579/614) e o import local redundante em `executar_analise_programada` (linha 1066); agora as 3 funções usam apenas o import global do topo (`from src.operator_status import obter_status_operadores`, linha 60). Bug confirmado antes da correção: com `PYTHONPATH=/opt/leon/app:/opt/leon/app/src` (mesmo do systemd), `operator_status` e `src.operator_status` eram módulos distintos em memória. Testes: 398/398 passando. **Achado colateral (fora do escopo, não corrigido)**: `backups/leon_backup_20260805/` contém backups aninhados recursivamente (dezenas de níveis) incluindo cópia antiga de `test_leon_brain.py`; roda `pytest` sem escopo (ex: `pytest .` na raiz) causa `INTERNALERROR` por `sys.exit(0)` dentro do backup. Sempre rodar testes com `pytest tests/ --ignore=tests/test_leon_brain.py`, nunca `pytest .`.
- [x] **Missão 2 — Import quebrado do Telegram `/status`** ✅ CONCLUÍDA (2026-08-18, sem commit — aguardando aprovação): `telegram_commands_mcp.py:640` importava `detectar_ativo` de `market_reader.py` (módulo só tem `ler_preco_xau`) → `ImportError` mascarado pelo `except Exception`, `/status` sempre caía no fallback fixo `Gold_Spot`. Corrigido para `from asset_detector import detectar_ativo` (mesmo padrão já usado em `mt5_monitor.py`, `mt5_execution_refiner.py`, `leon.py`, `mt5_engine.py`). Validado manualmente: `_formatar_status()` agora chama `detectar_ativo()` de verdade (retornou `Gold_Spot` real, não por fallback). Teste de regressão novo: `tests/test_telegram_commands_status.py` (2 testes — import correto sem exceção; `/status` reflete símbolo do cache, não o fallback fixo). Testes: 400/400 passando (398 + 2 novos).
- [ ] **Missão 3 — Remover código morto `context_decision`**: `interest_zone_engine.py:932-935` (`monitor_touched_zone`) importa módulo `context_decision` que não existe no repo. Função nunca chamada hoje; remover (ou criar o módulo, se houver uso planejado).
- [ ] **Missão 4 — Bug de risco: `max_risk_percent` nunca lido** (⚠️ pedir confirmação extra antes de implementar, mesmo pequena): `mt5_order_executor.py:227` faz `config.get("max_risk_percent", 1.0)` sobre `_execution_config()` (seção `[EXECUTION]`), mas a chave só existe em `risk_control_agent._risk_config()` (seção `[RISK_CONTROL]`). Teto de risco do lote fica sempre fixo em 1.0%, ignorando o valor real configurado.
- [ ] **Missão 5 — `telegram_config.py` não deve derrubar import por config inválido**: `int()` sobre `timeout`/`dedupe_seconds` em import-time sem try/except — valor não-numérico no `config.ini` quebra a importação de todos os módulos dependentes (leon_panel, telegram_commands_mcp, telegram_engine).
- [ ] **Missão 6 — Segurança: auth do painel**: `leon_panel.py` (`_is_authorized`) usa `==` em vez de `hmac.compare_digest` (timing attack) e aceita chave via query string (fica em logs/referrer).
- [ ] **Missão 7 — Duplicação em `leon_operator.py`**: ~12 funções quase idênticas (`_ler_ultima_X`/`_salvar_X`/`_deve_X` — coleta, análise, demo, estudo, status telegram) com a mesma lógica de comparar intervalo desde última execução. Extrair 2 helpers genéricos, redução estimada de ~300 linhas.
- [ ] **Missão 8 — Limpeza de código morto**: funções/classes/imports/variáveis nunca usadas em `leon.py` (`_CandlesIloc`, `_CandlesLeves`, `carregar_candles_para_bos`, `normalizar_bos`, `direcao_m15`), `leon_operator.py` (`_iniciar_identidade_ciclo`), `telegram_commands_mcp.py` (`_memory_error`/`_market_error`/`_backtest_error`/`_replay_error`, `ALLOWED_CHAT_IDS` nunca filtrado).
- [ ] **Missão 9 — Performance (painel + I/O)**: `leon_panel.py` lê `leon_log.txt` inteiro 3× por request `/api/status` (poll 10s); `mt5_order_executor.py` lê CSV de ordens 2× em sequência e CSV de candles inteiro só para última linha. Cache com TTL curto ou leitura por `seek`/tail.

**Fora do escopo imediato** (esforço grande, tratar em missão dedicada futura, só se autorizado): paths absolutos hardcoded em ~30 módulos (ignoram `paths.py` existente); `config_loader.py` canônico para unificar leitura de `config.ini` (hoje reaberto em ~8 módulos com defaults divergentes); redução de ciclos `mt5.initialize()/shutdown()` no executor (caminho crítico de execução, precisa de testes DEMO extensivos isolados).

**Status**: Missão 1 concluída e commitada. Missão 2 concluída (implementada + testada, sem commit — aguardando aprovação). Próxima ação: aguardar aprovação para commit da Missão 2 e/ou autorização para iniciar Missão 3.

## 🎯 Última Missão Concluída: Pendência #2 — Telegram REATIVADO (token real do BotFather)
- **Estado**: Telegram **ATIVO e operacional** — token real + chat_id configurados em `/opt/leon/app/.env` (`LEON_TELEGRAM_TOKEN`, `LEON_TELEGRAM_CHAT_ID=-1004376165028`, `LEON_TELEGRAM_ENABLED=true`); `config.ini` `[TELEGRAM] enabled = true`.
- **Validação em 3 camadas**: (1) `getMe` → `LeonXauEliteBot` válido; (2) `getChat` → supergrupo "LEON XAU AI - Estudos" válido; (3) envio real → `message_id 3364` entregue + log do operador `TELEGRAM | mensagem enviada com sucesso`.
- **Operador**: reiniciado (PID **3457923**) — processo vivo envia mensagens com sucesso.
- **⚠️ Decisão estrutural**: NÃO criar symlink `app/.env -> config/.env` — o `app/.env` tem chaves web reais (SECRET_KEY, admin) que não existem no `config/.env`; o placeholder antigo `COLAR_...` do `config/.env` seria lido como token. Fonte única efetiva: `/opt/leon/app/.env` + `config.ini`.
- **Arquivos**: `/opt/leon/app/.env` (credenciais, ignorado pelo git), `config.ini` (`enabled=true`, ignorado pelo git), `tarefas/aprendizados_diarios/CONTEXTO_EVOLUCAO.md`, `tarefas/aprendizados_diarios/2026-08-18.md`, `tarefas/handoff_atual.md` (este).
- **Sem commit** (aguardando autorização). Nenhuma alteração em MT5, risco, TP/SL ou execução.

## 🎯 Missão Anterior: Pendência #2 — Telegram alinhado DESABILITADO (config + doc)
- **Estado corrigido**: `config.ini` `[TELEGRAM] enabled = true` → `false` — runtime agora reporta `TELEGRAM_ENABLED = False` e `enviar_mensagem()` retorna `TELEGRAM_DISABLED` (antes: `enabled=true` sem token → `TELEGRAM_CONFIG_MISSING`, estado inconsistente com o handoff).
- **Causa da inconsistência**: `telegram_config.py` lê `ROOT_DIR/.env` (= `/opt/leon/app/.env`, arquivo real sem chaves Telegram) + `config.ini` como fallback. O `/opt/leon/config/.env` (com `LEON_TELEGRAM_ENABLED=false` + token placeholder `COLAR_...`) **NÃO é lido pelo runtime** — o symlink `app/.env -> config/.env` documentado em 22/07 foi sobrescrito em 27/07 por `.env` real (chaves web).
- **Risco documentado**: NÃO recriar o symlink enquanto o token em `/opt/leon/config/.env` for placeholder `COLAR_...` (seria lido como token configurado → POST inválido). Reativação exige token real do BotFather + `enabled = true` + teste de envio real.
- **Testes**: 39 telegram + suíte completa **398 passed** (`--ignore=tests/test_leon_brain.py`). Runtime validado: `TELEGRAM_ENABLED=False`, `TELEGRAM_DISABLED` no guard.
- **Arquivos**: `config.ini` (`enabled=false`), `tarefas/aprendizados_diarios/CONTEXTO_EVOLUCAO.md` (linha Telegram atualizada), `tarefas/aprendizados_diarios/2026-08-18.md` (aprendizado), `tarefas/handoff_atual.md` (este).
- **Sem commit** (aguardando autorização). Nenhuma alteração em código operacional, MT5, risco, TP/SL ou execução.

## 🎯 Missão Anterior: MISSION-20260818-FIX-MCP-MARKET (bug #12)
- **Bug corrigido**: `leon_market_mcp.py` importava `_MT5_AVAILABLE` por valor (cópia `False` no import) → todos os tools de mercado exceto `check_mt5_status` retornavam "MT5 não disponível" mesmo com MT5 saudável. Mesmo padrão em `leon_backtest_mcp.py`.
- **Correção**: helper `_mt5_disponivel()` → `check_mt5().get("available")` (dispara `_ensure_initialized()` real) nos 6 handlers do market MCP; backtest usa `check_mt5().get("available")` no lugar da flag estática.
- **Status**: ✅ IMPLEMENTADA + TESTADA + VALIDADA EM PRODUÇÃO (aguardando commit)
- **Testes**: 11 novos em `tests/test_market_mcp_availability.py`; suíte completa **398 passed** (`--ignore=tests/test_leon_brain.py`)
- **Validação em produção (MCP real via JSON-RPC)**: `get_account_info` → balance 10100.54, equity 10097.06, leverage 100 (antes: "MT5 não disponível"); `get_current_price Gold_Spot` → bid 4393.67/ask 4393.99; `get_ohlc` M15 real; `list_symbols` → Gold_Spot encontrado. Símbolo ativo da corretora: **Gold_Spot** (não XAUUSD).
- **Segurança**: nenhuma função de ordem exposta; somente leitura; conta real bloqueada.
- **Arquivos**: `src/mcp/leon_market_mcp.py`, `src/mcp/leon_backtest_mcp.py`, `tests/test_market_mcp_availability.py` (novo)

## 🎯 Missão Anterior: MISSION-20260818-CORRECAO-ENTRADA-SMC (encerramento pós-commit)
- **Commit `d1e6ba3`** (06:25:46) e **restart do operador às 06:27:01** — operador PID **3424309** JÁ roda o código novo (SMC guard sempre ativo em LAB_LEARNING; `_micro_trigger` com sweep+reclaim+displacement, sem perseguir estrutura).
- **Status**: ✅ IMPLEMENTADA + COMMITADA + VALIDADA (missão encerrada; ver MISSION-20260818-CORRECAO-ENTRADA-SMC.md)
- **Evidência em produção (Fase A)**: log 06:35+ mostra "SMC guard sempre ativo, timeframe_policy relaxado pelo laboratorio" (antes do restart: "SMC guard skipped"); PREOP-003551 em loop sem nova entrada — bloqueado por `MAX_OPEN_POSITIONS_REACHED` (2 abertas, limite 2), não mais pelo viés comprar topo/vender fundo.
- **Autonomia**: ativa (demo_execution) até 2026-08-18T20:32:24; heartbeat ONLINE (PID 3424309, `execution_authorized: true`); conta real bloqueada.
- **Achado novo (bug MCP, SEM correção nesta missão)**: `src/mcp/leon_market_mcp.py` importa `_MT5_AVAILABLE` **por valor** (cópia `False` no import) → todos os tools de mercado exceto `check_mt5_status` retornam "MT5 não disponível" mesmo com MT5 saudável (rpyc OK, porta 18812 aberta). A flag só é atualizada dentro de `mt5_safe`; os handlers não chamam `_ensure_initialized()`/`check_mt5()` antes. **Correção proposta**: handlers devem chamar `check_mt5()`/`_ensure_initialized()` antes de checar a flag, ou importar o módulo e ler `mt5_safe._MT5_AVAILABLE` dinamicamente. → Pendência nova #12.

## 🎯 Missão Anterior: MISSION-20260818-BACKUP-RESGATE-DADOS
- **Fase 2 do plano de execução** (pendências #6 e #9)
- **Status**: ✅ CONCLUÍDA
- **Backup automático dos CSVs operacionais**: `scripts/backup_operational_data.sh` (backup/status/verify), snapshot leve 1.5M, checksum sha256, rotação 48, agendado no crontab do `leon` (`0 * * * *`)
- **Resgate do gap 12-17/08**: gap ERA recuperável (pendência #6 estava incorreta). Backup `leon_20260817_031822.tar.gz` (03:18, anterior ao incidente das 21:03) preservou a janela. Merge não-destrutivo aplicado: 73 → **297 pre-ops** (224 recuperadas, 103 fechadas com resultado). Swap atômico, perm/owner preservados.
- **Incidente secundário corrigido**: `logs/operator_out.log` era `root:leon` (640) → restart automático do operador estava quebrado. Log removido, operador reiniciado (**PID 3395248**).
- **Testes**: 373 passed (`--ignore=tests/test_leon_brain.py`)
- **Rollback**: snapshot `opdata_20260818_053146.tar.gz` guarda a versão pré-swap (74 linhas)
- **Doc**: `tarefas/missoes/MISSION-20260818-BACKUP-RESGATE-DADOS.md`

## Missão Anterior: MISSION-20260817-BASE-DIAS-CORRIDOS
- **Base de desempenho trocada de contagem para janela de dias corridos** (`[BASELINE] window_days = 30`)
- **Status**: ✅ APROVADO (Architect: APROVADO COM AJUSTES; Reviewer: APROVADO COM RESSALVAS, corrigidas)
- **Testes**: 373 passed, 0 falhas (`--ignore=tests/test_leon_brain.py`)
- **Arquivos**: `src/baseline_window.py` (novo), `tests/test_baseline_window.py` (novo, 17 testes), `pre_operation_engine.py`, `learning_bootstrap.py`, `operation_readiness.py`, `lab_entry_policy.py`, `operation_batch_review.py`, `leon_panel.py`, `test_performance_engine.py`, `config.ini` + `config.ini.example`

## 🚨 Incidente Tratado (severidade ALTA)
- `tests/test_performance_engine.py` truncou `data/pre_operation_trades.csv` real (370 linhas → header) em 17/08 21:03 ao rodar a suíte
- **Causa raiz**: teste escrevia/apagava no `data/` real (sem tmp_path) — landmine pré-existente
- **Correção**: fixture autouse `_isolar_csv(tmp_path, monkeypatch)`; validado CSV intacto (md5 idêntico antes/depois)
- **Recuperação**: NÃO recuperável integralmente (197 operações fechadas 12-17/08 perdidas; nenhum CSV residual tem resultado/data_fechamento; backups até 05/08)
- **Integridade**: sequence_file preservou numeração (novo = PREOP-003478, sem colisão)
- **Operador**: ONLINE, autonomia ATIVA, CSV repopulando

## 📁 Arquivos Modificados (missão)
| Arquivo | Mudança |
|---------|---------|
| `src/baseline_window.py` | NOVO — helper de janela (obter_window_days, parse_datetime, dentro_da_janela) |
| `tests/test_baseline_window.py` | NOVO — 17 testes |
| `src/pre_operation_engine.py` | `resumo_pre_operacao(window_days=None)`; `ultimo/total/abertos` globais |
| `src/learning_bootstrap.py` | `_winrate_shadows_recentes(window_days)` |
| `src/operation_readiness.py` | passa `obter_window_days()`; expõe `window_days` em rules |
| `src/lab_entry_policy.py` | `shadow_evidence(window_days)`; janela só na produção |
| `src/operation_batch_review.py` | janela + dedup por `operation_ids` + seed migração |
| `src/leon_panel.py` | novas chaves do state batch_learning |
| `tests/test_performance_engine.py` | isolamento tmp_path (correção incidente) |
| `config.ini` + `config.ini.example` | seção `[BASELINE] window_days = 30` |

## 📋 Pendências Pós-Missão
0. **MT5 indisponível (24/08)** — `IPC send failed` (-10001); restart manual de rpyc+MT5 headless necessário (ver missão acima). Bloqueia validação end-to-end do B2 e toda leitura MT5.
1. **Rotacionar senha do usuário `jhonatan`** (dashboard web) — comprometida em 30/07
2. **Telegram** — ✅ REATIVADO (2026-08-18): token real do BotFather + chat_id `-1004376165028` configurados em `/opt/leon/app/.env`; `config.ini` `enabled=true`; envio real validado (`message_id 3364`, grupo "LEON XAU AI - Estudos"). ⚠️ NÃO criar symlink `app/.env -> config/.env` (placeholder antigo `COLAR_...` no `config/.env` seria lido como token; `app/.env` tem chaves web reais).
3. **Backtest MCP** — ainda simulação estrutural (`candles_analyzed: 0`)
4. **Persistir razão do bloqueio de auto-simulate** (achado C5) — hoje só vai ao stdout
5. **Renovar autorização demo semanalmente** — operador NÃO renova automaticamente quando `AUTONOMY_EXPIRED`
6. ~~**Gap de dados 12-17/08**~~ ✅ RESOLVIDO (MISSION-20260818): gap ERA recuperável. 224 pre-ops recuperadas do backup `leon_20260817_031822.tar.gz`. Restante: fatia PREOP-003330→003477 (17/08 03:18→21:03) só existe em 67 `.txt` — sub-tarefa opcional (parser dos .txt), tratar depois.
7. **Dívida técnica**: `_consecutive_losses()` ainda por contagem; consumidores `performance_engine`, `risk_method_engine`, `telegram_commands_mcp`, `daily_learning_report` calculam winrate sem janela
8. **`tests/test_leon_brain.py`** usa `sys.exit(0)` no módulo — suíte exige `--ignore` (dívida conhecida)
9. ~~**Backup externo dos CSVs de `data/`**~~ ✅ RESOLVIDO (MISSION-20260818): `scripts/backup_operational_data.sh` implantado (snapshot 1.5M somente-leitura, sha256, rotação 48) e agendado no crontab do `leon` (`0 * * * *`). Log em `/opt/leon/logs/backup_operational_data.log`. Validado em `env -i`.
11. **Restart automático do operador era falha silenciosa** (descoberto em 2026-08-18): `logs/operator_out.log` pertencia a `root:leon` (640) e o `start-operator.sh`, rodando como `leon`, falhava com `Permission denied` — o operador não voltaria sozinho se caísse. Log removido e operador reiniciado. **Pendente**: impedir recorrência (evitar que processo root crie logs do operador; considerar `logrotate` com `su leon leon` ou criar o log com owner correto no script).
10. ~~**🔴 CRÍTICA — Correção do gatilho de entrada + guard de posição SMC**~~ ✅ IMPLEMENTADO + COMMITADO (MISSION-20260818-CORRECAO-ENTRADA-SMC, commit `d1e6ba3`): LEON estava **comprando topo e vendendo fundo** (winrate VENDA-FUNDO = 17.6%, COMPRA-TOPO = 41%; mediana posição: COMPRA 0.67 / VENDA 0.23 do range 48h). Correções aplicadas no escopo **A + C** (escolha do usuário): **A** — `_micro_trigger` reescrito: confirmação exige sweep de liquidez + reclaim + displacement e NUNCA rompimento de estrutura (anti perseguir preço); **C** — `create_lab_zone` não fabrica mais `CONFIRMADA` (nasce `AGUARDANDO_ESTRUTURA`, sem `structural_confirmations`/`valid_confirmations` fabricados) e SMC guard passou a ser **sempre ativo** (LAB_LEARNING não pula mais o guard). Guard de posição 3.2 (hard block) **NÃO implementado** — sem evidência nos dados recuperados. 387 testes passando. Reviewer: APROVADO COM RESSALVAS (corrigidas). **Impacto operacional**: execução demo LAB via bootstrap fica bloqueada até existir mecanismo de confirmação estrutural real (follow-up) — ver relatório da missão.
12. ~~**Bug MCP `_MT5_AVAILABLE` copiado por valor**~~ ✅ RESOLVIDO (MISSION-20260818-FIX-MCP-MARKET): `leon_market_mcp.py` importava a flag `False` por valor → `get_account_info`, `get_current_price`, `get_symbol_info`, `get_ohlc`, `list_symbols`, `get_market_snapshot` retornavam sempre "MT5 não disponível"; só `check_mt5_status` funcionava. Correção: helper `_mt5_disponivel()` → `check_mt5().get("available")` (dispara `_ensure_initialized()` real). Mesmo padrão corrigido em `leon_backtest_mcp.py`. Validado em produção (account info real, preço Gold_Spot real). 11 testes novos, 398 total.

## 🟢 Status Geral do Sistema
- **416/416** testes passando (com `--ignore=tests/test_leon_brain.py`) — inclui 13 novos do B2 (`tests/test_lab_zone_monitor.py`)
- **🔴 MT5**: INDISPONÍVEL desde 24/08 (`IPC send failed` -10001) — porta 18812 abre mas IPC falha; suspeita de sessões wineserver dessincronizadas (rpyc 20:08 vs terminal64 21:00). Restart manual pendente do usuário.
- **Operator**: rodando código de 21/08 (commit `c3420e2`) — **NÃO inclui ainda o hook B2** (restart pendente de autorização). Autonomia demo EXPIRADA desde 21/08 14:30. Conta real bloqueada.
- **CSV pre_operation**: 297+ pre-ops (PREOP-003106→003558), gap 12-17/08 recuperado; 18 ABERTO, 137 FECHADO, 150 OBSERVADO
- **Backup operacional**: horário via `scripts/backup_operational_data.sh` → `/opt/leon/backups/operational_data/` (rotação 48)
- **MCPs**: backtest, market, memory, replay registrados — market MCP funcional quando MT5 saudável
- **Zonas LAB**: 1571 total — 1509 legadas CONFIRMADA (artefatos pré-18/08, fora de escopo), 62 AGUARDANDO_ESTRUTURA (legítimas, agora monitoráveis pelo B2 após restart do operador com MT5 saudável)
- **Alerta operacional (pendência #10)**: ✅ RESOLVIDO — operador roda o guard SMC novo; entradas no quadrante comprar topo/vender fundo não passam mais