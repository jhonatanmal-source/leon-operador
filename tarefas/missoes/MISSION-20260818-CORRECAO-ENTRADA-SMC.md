# MISSION-20260818-CORRECAO-ENTRADA-SMC — Relatório

**Status:** IMPLEMENTAÇÃO CONCLUÍDA — aguardando aprovação/autorização de commit
**Data:** 2026-08-18
**Classificação:** IA / OPERACIONAL LEON / DADOS (correção crítica de viés de entrada)
**Pendência resolvida:** #10 (🔴 CRÍTICA — comprar topo / vender fundo)

---

## 1. Escopo (decisão do usuário)

O usuário escolheu **A + C**:
- **A** — corrigir gatilho M5 de rompimento para reteste/sweep+reclaim (`_micro_trigger`).
- **C** — fechar brechas estruturais: `create_lab_zone` fabricava `CONFIRMADA`; `LAB_LEARNING` dava skip no SMC guard.

**Fora do escopo:** opção B (instrumentação), guard de posição 3.2 (hard block — rejeitado por falta de evidência nos dados recuperados: grupo bloqueado performava melhor que aprovado), alteração de estratégia/risco/TP/SL, conta real, envio de ordens.

## 2. Causas raiz confirmadas (diagnóstico)

1. `src/mt5_execution_refiner.py` `_micro_trigger`: `confirmed = structure_break or (reaction and displacement)` — rompimento confirmava (comprar topo / vender fundo).
2. `src/smc_entry_guard.py` `validate_smc_entry`: guard só de rótulos (sem preço/estrutura) — **não alterado** (fora de escopo).
3. `src/institutional_analysis_engine.py`: `premium_discount_ok` só pontua +10 (não gate) — **mantido** (decisão).
4. `src/interest_zone_engine.py` `create_lab_zone`: fabricava `region_status=CONFIRMADA` + confirmações `LAB_APPROVED`/`LAB_ENTRY` falsas.
5. `src/mt5_order_executor.py` rota `LAB_LEARNING`: pulava SMC guard e timeframe policy para zonas LAB.

## 3. Alterações implementadas

| Arquivo | Mudança |
|---------|---------|
| `src/mt5_execution_refiner.py` | `_micro_trigger` reescrito: `confirmed = swept and reaction and displacement and not structure_break`. Sweep = varredura do extremo oposto; reclaim = fechamento a favor; displacement = corpo/range ≥ 0.55. Contrato de retorno preservado + campos aditivos `sweep`, `reclaim`, `swing_low`, `swing_high`. |
| `src/interest_zone_engine.py` | `create_lab_zone`: `region_status` `CONFIRMADA` → `AGUARDANDO_ESTRUTURA`; `structural_confirmations`/`valid_confirmations` fabricados → `[]`; adicionado `lab_brain_score` como metadado observável; docstring com nota operacional honesta. |
| `src/mt5_order_executor.py` | SMC guard **sempre ativo** (removido o skip em LAB_LEARNING); comentário/log atualizado. |
| `tests/test_execution_refiner.py` | **NOVO** — 12 testes do gatilho M5 (rompimento NÃO confirma, sweep+reclaim confirma, borda close==swing_low, contrato, integração leve). |
| `tests/test_mt5_order_executor.py` | `test_lab_bypasses_smc_guard` → `test_lab_respects_smc_guard` (novo contrato: SMC guard bloqueia mesmo em LAB). |
| `tests/test_interest_zone_engine.py` | 2 testes novos: zona LAB não nasce CONFIRMADA; zona LAB bloqueada pelo guard de execução. |

## 4. Testes

- Suíte completa: **387 passed** (`--ignore=tests/test_leon_brain.py` — falha pré-existente documentada por `sys.exit(0)`).
- Novos: 12 (refiner) + 2 (interest zone) + 1 atualizado (executor) = 15 testes tocados.

## 5. Revisão (Engineering Reviewer)

**Veredito: ✅ APROVADO COM RESSALVAS** — nenhum bloqueador.
- Achado MEDIA (corrigido): docstring de `create_lab_zone` prometia promoção estrutural que não existe no fluxo — nota operacional adicionada.
- Achado BAIXA (corrigido): comentário/log obsoleto no LAB_LEARNING.
- Achado BAIXA (corrigido): teste de borda `close == swing_low` adicionado.
- Achado BAIXA (opcional, não feito): teste de promoção LAB via `monitor_zone` com evidência real — registrado como follow-up.

## 6. Segurança

- Nenhum guard removido — guard reforçado (SMC sempre ativo; zona LAB não executável sem confirmação real).
- Nenhuma alteração de estratégia/risco/TP/SL; conta real bloqueada; nenhuma ordem enviada durante a missão.
- Nenhum segredo exposto; diffs revisados.

## 7. Impacto operacional (importante)

1. **Caminho LAB demo via bootstrap fica bloqueado**: o fluxo `leon.py` cria zona LAB mas não alimenta evidência estrutural real para promovê-la a `CONFIRMADA`. Execução demo LAB fica permanentemente bloqueada até existir mecanismo de confirmação estrutural real (follow-up de produto).
2. **Operador em execução (PID 3395248) ainda roda o código antigo**: a correção entra em vigor no próximo restart do operador — requer autorização explícita.
3. **Novas pre-ops LAB** continuam sendo registradas (observabilidade preservada) mas **não executam** mais.

## 8. Follow-ups registrados

- Mecanismo de confirmação estrutural real para zonas LAB (reativar aprendizado demo com segurança).
- Instrumentação de posição da entrada vs estrutura (opção B) quando houver dados suficientes.
- Teste de promoção LAB via `monitor_zone` com evidência (opcional).

## 9. Aprovação

**Aguardando autorização do usuário para:**
- [ ] Commit das alterações (src + tests + tarefas)
- [ ] Restart do operador para aplicar a correção
