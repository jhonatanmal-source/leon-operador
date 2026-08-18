# PLANO DA MISSÃO — MISSION-20260817-CORRECAO-ENTRADA-SMC

- **Data**: 2026-08-17
- **Classificação**: OPERACIONAL LEON / SMC / MT5 (somente análise e guard — sem ordens reais)
- **Status**: ⏳ PLANO PRONTO — AGUARDANDO AUTORIZAÇÃO DO USUÁRIO
- **Diretor**: LEON Engineering Director

---

## 1. PROBLEMA (evidência)

O LEON está **comprando topo e vendendo fundo** — viés sistemático de posição de entrada, confirmado em 62 shadow trades fechados:

| Quadrante | Trades | Winrate | Avaliação |
|-----------|--------|---------|-----------|
| COMPRA em TOPO (pos≥66%) | 17 | 41% | ⚠️ comprando topo |
| VENDA em FUNDO (pos≤33%) | 17 | **17.6%** | 🔴 vendendo fundo |
| COMPRA em FUNDO (pos≤33%) | 11 | 36% | ✅ correto |
| VENDA em TOPO (pos≥66%) | 3 | 33% | ✅ correto |

Mediana da posição da entrada no range 48h: **COMPRA = 0.67** (topo) | **VENDA = 0.23** (fundo).

## 2. CAUSA RAIZ (diagnóstico Trading Systems Engineer — somente leitura)

1. **`_micro_trigger`** (`src/mt5_execution_refiner.py`, linhas 85-119): gatilho de **ROMPIMENTO/momentum** — COMPRA dispara quando o close rompe o topo recente, VENDA quando rompe o fundo. Isso é *chasing* (entrar no deslocamento), violando a regra "Não entrar no meio do movimento".
2. **`build_smc_trade_levels`** (`src/smc_price_levels.py`): a zona usada é o **FVG de deslocamento** (gap na ponta do impulso), não zona de demanda/oferta. Não exige reteste, premium/discount, proximidade de swing.
3. **Ausência de guard de posição** em todas as camadas (`smc_entry_guard` valida só rótulos; `premium_discount_ok` = +10/35, não bloqueia).
4. **`create_lab_zone`** (`src/interest_zone_engine.py`): fabrica zonas `CONFIRMADA` para burlar guard no bootstrap.

## 3. ESCOPO DA CORREÇÃO (proposta)

### 3.1 Crítico — gatilho de reteste (substituir rompimento)
- `mt5_execution_refiner._micro_trigger`: COMPRA só confirma quando preço **retorna à zona** (FVG/OB/demanda) após deslocamento e mostra reação (rejeição/liquidez varrida). Não mais disparar por rompimento do range recente.

### 3.2 Alto — guard de posição da entrada vs estrutura (hard block)
- Novo guard obrigatório (ex.: `validate_entry_position`): COMPRA exige entrada na metade inferior (discount) do range estrutural (`pos ≤ 0.5` do range 48h/M15-H1) e próxima de zona de demanda; VENDA simétrica (premium + supply). **Hard block**, não fator de pontuação.
- `premium_discount_ok` passa a ser **gate obrigatório** (não +10 pontos).
- Revisar rota `_VIA_ABC_RANGE` para exigir validação de posição.

### 3.3 Alto — seleção da zona correta
- `build_smc_trade_levels`: exigir zona de demanda/oferta real (OB, FVG mitigado, demand/supply zone) + reteste da zona, não apenas "dentro do gap".
- Proibir `create_lab_zone` de fabricar zonas `CONFIRMADA` sem evidência estrutural; zona de laboratório passa pelos mesmos guards.

### 3.4 Médio — evidência e observabilidade
- Segmentar evidência shadow por posição no `lab_entry_policy.py` (não contar VENDA-FUNDO/COMPRA-TOPO como evidência elegível até o guard existir).
- Registrar `pos` no CSV shadow (coluna nova).
- Expor mediana de posição por direção no web panel.

## 4. FORA DE ESCOPO (protegido)

- Estratégia, risco, TP/SL (regras do operacional oficial)
- Envio de ordens MT5
- Conta real (permanece bloqueada)
- Remoção de guards existentes (apenas adição)
- Alteração do operacional sem autorização

## 5. RISCOS

| Risco | Mitigação |
|-------|-----------|
| Overfitting no guard de posição (parâmetros muito restritivos) | Validar contra 62 shadows históricos; aceitar redução de trades por segurança |
| Quebra de contratos de teste existentes | Mocks de teste atualizados junto; suíte completa obrigatória |
| Menos entradas (gatilho mais seletivo) | Esperado e desejável — qualidade > quantidade |

## 6. CONVOCAÇÃO PROPOSTA

| Agente | Papel |
|--------|-------|
| Trading Systems Engineer | Análise SMC e definição de parâmetros do guard |
| Senior Software Engineer | Implementação |
| QA Test Engineer | Testes (gatilho de reteste, guard de posição, regressão 62 shadows) |
| Software Architect | Revisão de contrato |
| Engineering Reviewer | Revisão final |

## 7. CRITÉRIOS DE ACEITE

- [ ] Gatilho de reteste implementado (sem disparo por rompimento)
- [ ] Guard de posição hard block ativo em todas as rotas de entrada
- [ ] `create_lab_zone` não fabrica zonas sem evidência
- [ ] Suíte completa passando (373+ testes)
- [ ] Replay dos 62 shadows: distribuição de posição melhora (mediana COMPRA < 0.5, VENDA > 0.5) nos novos shadows
- [ ] Segurança: conta real bloqueada, nenhuma ordem real

## 8. FASE ATUAL

- [x] TRIAGEM
- [x] DIAGNÓSTICO (evidência 62 trades + análise de código)
- [x] PLANO (este documento)
- [ ] CONVOCAÇÃO (aguarda autorização)
- [ ] IMPLEMENTAÇÃO
- [ ] TESTES
- [ ] REVISÃO
- [ ] SEGURANÇA
- [ ] DOCUMENTAÇÃO
- [ ] RELATÓRIO
- [ ] APROVAÇÃO

---

*Plano elaborado em 2026-08-17. Nenhuma alteração de código foi feita. Nenhuma ordem enviada. Conta real bloqueada.*
