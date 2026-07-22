# STATUS A02 — Corrigir: Conectar Gate Estrutural ao Pipeline Real

## Veredito Final: **APROVADO**

---

## Causa Raiz

O módulo `interest_zone_engine.py` continha `validate_zone_for_execution()` chamando `evaluate_live_confirmation_gate()` (o gate estrutural canônico), mas **nenhum código de produção o invocava**. O executor (`mt5_order_executor.py`) não exigia validação estrutural da região antes de prosseguir com a ordem.

## Fluxo Anterior

```
registrar_pre_operacao()              → Cria PRE_OPERATION sem region_id
executar_ordem_mt5_pre_operacao()     → Pula validação estrutural da zona
                                      → Vai direto para SMC, sessão, notícias, etc.
                                      → order_send sem verificar zona canônica
```

## Fluxo Depois

```
registrar_pre_operacao(region_id)     → Se ABERTO + region_id presente:
                                        → validate_zone_for_execution()
                                        → Se falha → status OBSERVADO
                                        → Persiste structural_gate_version, timestamp, resultado
                      ↓
executar_ordem_mt5_pre_operacao()     → Após encontrar PRE_OPERATION:
                                        → validate_zone_for_execution() obrigatório
                                        → Se falha → bloqueio imediato
                                      → Demais guards (SMC, sessão, risco, etc.)
                                      → order_send
```

## Ponto Exato de Integração

- **Registro:** `src/pre_operation_engine.py:registrar_pre_operacao()` — gate executado ao criar PRE_OPERATION com status ABERTO
- **Execução:** `src/mt5_order_executor.py:executar_ordem_mt5_pre_operacao()` L593 — gate executado logo após encontrar PRE_OPERATION aberta

## Campos Adicionados à PRE_OPERATION

| Campo | Tipo | Descrição |
|---|---|---|
| `region_id` | str | Identificador canônico da região |
| `structural_gate_version` | str | Versão do contrato (`LEON_CAUSAL_CONTRACT_V2`) |
| `structural_gate_timestamp` | str | ISO timestamp da avaliação do gate |
| `structural_gate_result` | str | Resultado do gate (`PASSED` ou código de erro) |

## Forma de Impedir Evidência Obsoleta

O `validate_zone_for_execution()` é chamado **no momento da execução** (não apenas no registro). Ele reavalia:
- Se a região ainda existe no InterestZoneStore
- Se a região não foi invalidada
- Se a janela não expirou
- Se as confirmações estruturais continuam válidas
- Se o status da região ainda é CONFIRMADA

Isso garante que mesmo que o snapshot mude entre o registro e a execução, o gate rejeitará.

## Arquivos Modificados

| Arquivo | Alteração |
|---|---|
| `src/pre_operation_engine.py` | Adicionados `region_id`, `structural_gate_*` ao CAMPOS; `region_id` ao `registrar_pre_operacao()`; validação estrutural no registro ABERTO |
| `src/mt5_order_executor.py` | Import e chamada de `validate_zone_for_execution()` após encontrar PRE_OPERATION aberta |
| `tests/test_mt5_order_executor.py` | Fixture `mock_mt5` usa `sys.modules`; `mock_pre_op_csv` inclui novos campos; `mock_deps` com return_values reais para Python 3.12; corrigido `test_limite_diario_atingido` erro string; adicionados `test_structural_gate_blocks_sem_region_id` e `test_happy_path_demo_executes_order` |

## Testes Antes e Depois

### Antes (baseline): 112 passed, 4 failed, 2 errors
### Depois: 117 passed, 3 failed, 0 errors

**Testes aprovados:**
- `test_operational_contract.py` — 11/11 (gate unitário)
- `test_mt5_order_executor.py` — 8/8 → 10/10 (2 novos: gate sem region_id, happy path)
- `test_risk_control_agent.py` — 6/9 (3 falhas pré-existentes não relacionadas)

### Testes Específicos Solicitados

```
python -m pytest tests/test_operational_contract.py -q   → 11 passed
python -m pytest tests/test_mt5_order_executor.py -q     → 10 passed
python -m pytest tests -q -k "operational_contract or interest_zone or pre_operation or executor or causal"  → 52 passed
python -m pytest tests -q                                 → 117 passed, 3 failed (pré-existentes)
```

## Evidência de Fail-Closed

- Sem `region_id` → `PRE_OPERATION_REGION_REQUIRED`
- Zona não encontrada → `REGION_NOT_FOUND`
- Símbolo diverge → `REGION_SYMBOL_MISMATCH`
- Região invalidada → `REGION_INVALIDATED`
- Status não CONFIRMADA → `REGION_NOT_CONFIRMED`
- Gate estrutural recusa → `REGION_CAUSAL_CONFIRMATION_REQUIRED`

## Evidência de Bloqueio REAL

`mt5_order_executor.py:720-725` — verifica `account.trade_mode != ACCOUNT_TRADE_MODE_DEMO` quando `config["demo_only"]` é True. Retorna `MT5_REAL_ACCOUNT_BLOCKED`.

## Evidência de que order_send foi apenas mockado

No teste `test_happy_path_demo_executes_order`, `order_send` é verificado com `mock_mt5.order_send.assert_called_once()`. O mock substitui `mt5linux_compat` em `sys.modules`, garantindo que nenhuma ordem real é enviada. Nenhum operador foi inicializado. Nenhuma conexão MT5 real foi estabelecida.

## Decisão sobre LEON_CAUSAL_CONTRACT_V2

**Formalizado.** A versão de contrato `LEON_CAUSAL_CONTRACT_V2` é agora persistida no campo `structural_gate_version` da PRE_OPERATION quando o gate estrutural passa. Isto a torna uma versão de contrato real, não mais um artefato de tarefa.

## Decisão sobre READY_TO_EXECUTE

**Não implementado.** O pipeline já representa o estado "pronto para executar" por composição de todos os guards em `executar_ordem_mt5_pre_operacao()`. Adicionar `READY_TO_EXECUTE` como estado persistido duplicaria essa lógica sem benefício de segurança, pois a validação estrutural já é refeita no momento da execução.

## Pendências

Nenhuma para A02. As 3 falhas em `test_risk_control_agent.py` são pré-existentes e não relacionadas a esta correção.
