# MISSION-20260824-PROMOCAO-ZONAS-LAB

## Objetivo
Resolver o bloqueio B2 identificado no diagnóstico de 2026-08-21 ("por que não executa ordens na demo"): zonas de laboratório (`create_lab_zone`) nascem em `AGUARDANDO_ESTRUTURA` desde a correção de 18/08 (pendência #10), mas nenhum processo alimentava evidência estrutural real ao `monitor_zone` para promovê-las a `CONFIRMADA`. Sem promoção, `validate_zone_for_execution` bloqueava toda execução demo LAB indefinidamente com `REGION_NOT_CONFIRMED`.

## Diagnóstico (evidência coletada antes de implementar)
- Único caminho legítimo para `CONFIRMADA`: `monitor_zone(zone, evidence)` (`interest_zone_engine.py:829-856`), exigindo cadeia completa liquidez → estrutura (BOS/CHoCH/MSS/displacement) → gatilho.
- Guard de execução (`live_operational_contract.evaluate_live_confirmation_gate`) exige adicionalmente `structural_confirmations`/`valid_confirmations` não vazios e `region_status == "CONFIRMADA"`.
- Nenhum processo chamava `monitor_zone` para zonas `zone_source="LABORATORIO"`.
- `monitor_touched_zone` (função existente) é código morto — importa módulo `context_decision` inexistente no repo (fica para a Missão 3 do backlog, tratada separadamente por decisão do usuário).
- Engine institucional (`institutional_analysis_engine.analyze_smc_context`) já produz as chaves de evidência necessárias (`bos`, `choch`, `bos_event.displacement`, `liquidity`), mesmo mapeamento usado nas zonas de produção (`interest_zone_engine.py:550-556`).
- Gatilho M5 anti-chase (`_micro_trigger`, corrigido em 18/08 na MISSION-20260818-CORRECAO-ENTRADA-SMC) disponível para servir como `trigger_confirmed`.
- Levantamento do dataset real (`data/interest_zones.json`, 1571 zonas LAB): 1509 já `CONFIRMADA` (artefatos legados anteriores à correção de 18/08, fabricados sem evidência) e 62 `AGUARDANDO_ESTRUTURA` (legítimas, criadas 18-21/08, pós-correção). Decisão: não reprocessar as 1509 legadas (fora de escopo; evita custo de MT5 por zona e evita expirá-las em massa por idade).

## Decisões aprovadas pelo usuário
1. Política de evidência: **cadeia completa** (igual produção), sem relaxamento para LAB.
2. Ponto de execução: **ciclo de estudo contínuo do operador** (`leon_operator.py`), não no mesmo ciclo de criação da zona.
3. Gatilho final: **`_micro_trigger` M5** (sweep + reclaim + displacement, anti comprar topo/vender fundo).
4. Escopo: **separado** da remoção do código morto `monitor_touched_zone` (Missão 3 do backlog, não executada aqui).

## Implementação

### Novo módulo `src/lab_zone_monitor.py`
- `monitorar_zonas_lab(*, store=None, now=None) -> dict`: ponto de entrada.
- Filtra zonas `zone_source="LABORATORIO"`, não terminais e **ainda não `CONFIRMADA`** (exclui os 1509 artefatos legados, fora de escopo desta missão).
- Agrupa zonas por símbolo e faz **uma única leitura MT5 por símbolo por ciclo** (`load_execution_candles`), evitando reabrir conexão MT5 por zona (otimização crítica: primeira versão abria conexão por zona e travava com muitas zonas pendentes).
- Para cada zona: `_micro_trigger(m5, direction)` (gatilho) + `analyze_smc_context(m15)` (SMC) → evidência mapeada (`_build_evidence`) → `monitor_zone(zone, evidence=...)`.
- **Nunca escreve `region_status` diretamente** — a promoção ocorre exclusivamente dentro de `monitor_zone`.
- Quando a zona é promovida a `CONFIRMADA` pelo `monitor_zone`, grava `structural_confirmations`/`valid_confirmations` com os eventos **realmente detectados** (BOS, CHoCH, liquidez, gatilho M5) — nunca fabricados.
- Zonas sem candles/mercado indisponível: `skip` sem alteração de estado.
- Persiste via `InterestZoneStore.upsert`.

### Hook no operador (`src/leon_operator.py`)
- Import `from src.lab_zone_monitor import monitorar_zonas_lab`.
- Chamada no ciclo de estudo contínuo (junto de `avaliar_entradas_simuladas`), com log do resultado (`monitoradas`, `promovidas`, `invalidadas`, `expiradas`). Erros são capturados e logados sem interromper o ciclo.

### Testes `tests/test_lab_zone_monitor.py` (13 casos)
Short-circuit sem zonas LAB; zona de produção ignorada; zona terminal ignorada; zona já `CONFIRMADA` não reprocessada (zero custo MT5); mercado indisponível → skip; candles insuficientes → skip; símbolo real propagado (nunca default `XAUUSD`); sem evidência não confirma; liquidez+estrutura sem gatilho fica `AGUARDANDO_CONFIRMACAO`; cadeia completa promove a `CONFIRMADA` **e** libera o guard `validate_zone_for_execution`; gatilho sozinho não fabrica confirmação; invalidação por preço; duas zonas do mesmo símbolo geram apenas uma leitura MT5.

## Testes e Validação
- `tests/test_lab_zone_monitor.py`: **13/13 passed**.
- Suíte completa (`pytest tests/ --ignore=tests/test_leon_brain.py`): **416 passed** (403 baseline + 13 novos).
- Validação com cópia do dataset real (`data/interest_zones.json`, nunca o arquivo original): execução completa sem erros, arquivo real **intacto** (md5 idêntico antes/depois).
- Validação end-to-end com MT5 vivo: **bloqueada por ambiente** — `mt5.initialize()` retornou `False` (`IPC send failed`, -10001) durante a missão. Diagnóstico preliminar: duas sessões wineserver distintas ativas simultaneamente (uma hospedando o `rpyc_classic.exe`, iniciada às 20:08; outra hospedando o `terminal64.exe` do MT5, iniciada às 21:00), possivelmente dessincronizadas. Investigação/restart delegado ao `leon-devops-engineer`, mas **bloqueado pela política de permissões** (`/opt/leon/scripts/` fica fora do workspace `/opt/leon/app` e a regra nega acesso a diretórios externos por padrão). Ação de restart requer intervenção manual do usuário via SSH fora deste ambiente.

## Segurança e Contratos
- Somente leitura de MT5 (candles); nenhuma função de ordem é chamada por este módulo.
- Nenhum guard removido — o mecanismo **fortalece** o caminho do guard existente (antes, o guard bloqueava permanentemente por falta de evidência; agora, evidência real pode liberá-lo legitimamente).
- Conta real, estratégia, risco, TP/SL: **não alterados**.
- Nenhuma tentativa de contornar a restrição de diretório externo; nenhum processo MT5/wine foi tocado ou reiniciado.
- Sem commit (aguardando autorização); sem restart do operador (`leon_operator.py`) em produção.

## Arquivos Modificados
| Arquivo | Mudança |
|---|---|
| `src/lab_zone_monitor.py` | **Novo** — monitoramento e promoção de zonas LAB por evidência real |
| `src/leon_operator.py` | Import + chamada de `monitorar_zonas_lab()` no ciclo de estudo contínuo (+19 linhas) |
| `tests/test_lab_zone_monitor.py` | **Novo** — 13 testes |

## Pendências / Follow-ups
1. **MT5 indisponível** (`IPC send failed`) — restart manual necessário (`start-rpyc-server.sh` → `run-mt5-headless`, fora do workspace). Bloqueia validação end-to-end desta missão e qualquer operação de leitura MT5 no momento.
2. **1509 zonas LAB legadas `CONFIRMADA`** (fabricadas antes da correção de 18/08) permanecem no dataset sem reprocessamento — decisão consciente de escopo, não um bug. Se necessário revisitar (ex.: auditoria retroativa ou expurgo), tratar em missão dedicada.
3. **Restart do operador** para carregar o código novo (`leon_operator.py` com o hook) — requer autorização e reinicialização separada, não realizada nesta missão.
4. **Missão 3 do backlog** (remover `monitor_touched_zone` morto, que importa `context_decision` inexistente) permanece pendente, tratada separadamente por decisão do usuário.
5. Após restart do operador com MT5 saudável, monitorar nos logs: `OPERATOR | zonas LAB monitoradas: ...` para confirmar comportamento em produção nas 62 zonas legítimas pendentes.

## Status
✅ **IMPLEMENTADA + TESTADA** (416/416 testes passando). ⚠️ Validação end-to-end com MT5 vivo pendente (bloqueio de infraestrutura, fora do controle desta missão). Sem commit, sem restart do operador — aguardando aprovação do usuário.
