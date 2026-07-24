import sys
import os
import json
sys.path.insert(0, '/opt/leon/app')

os.environ['LEON_BRAIN_ENABLED'] = 'false'
os.environ['LEON_BRAIN_SHADOW_MODE'] = 'true'

from src.leon_brain import LeonBrain, OperationalBrainContext, BrainValidator
from src.leon_brain.brain_models import BrainConclusion, MemoryStatus, BrainEvidence, BrainResult, MCPStatus


PASS = 0
FAIL = 0
TOTAL = 0

def test(name, condition, detail=""):
    global PASS, FAIL, TOTAL
    TOTAL += 1
    if condition:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} {detail}")

print("=== FASE 11 — TESTES LEON BRAIN ===")
print()

print("--- Teste 1: Feature flag desligada ---")
brain = LeonBrain()
assert not brain.is_enabled, "LEON_BRAIN_ENABLED=false deveria resultar em is_enabled=False"
assert brain.is_shadow_mode, "Shadow mode deveria estar ativo"
test("Feature flag false resulta em disabled", not brain.is_enabled)
test("Shadow mode true por padrao", brain.is_shadow_mode)

print()
print("--- Teste 2: Brain desligado retorna comportamento identico ---")
ctx = OperationalBrainContext(
    timestamp="2026-07-24T10:00:00",
    symbol="XAUUSD",
    price=2500.0,
    macro_trend="ALTA",
    top_down_status="ALINHADO",
    session="LONDON",
    killzone="LONDON_OPEN",
    direction="COMPRA",
    smc_state="BOS_CONFIRMADO",
    elliott_state="ONDA_3",
    fibonacci_context="RETRACAO_61.8",
    liquidity_context="ACIMA",
    zone_id="Z001",
    zone_type="ORDER_BLOCK",
    zone_timeframe="M15",
    touch_status="TOQUE_CONFIRMADO",
    structural_confirmation="COMPLETA",
)
result = brain.process_context(ctx)
test("Brain desligado retorna resultado sem erro", result is not None)
test("Brain desligado summary indica desligado", "desligado" in result.summary.lower())

print()
print("--- Teste 3: BrainValidator - can_execute sempre false ---")
bval = BrainValidator()
res1 = BrainResult()
test("can_execute retorna False", not res1.can_execute())
test("can_alter_order retorna False", not res1.can_alter_order())
test("can_alter_risk retorna False", not res1.can_alter_risk())
test("can_alter_sl_tp retorna False", not res1.can_alter_sl_tp())

print()
print("--- Teste 4: BrainValidator - validate_result vazio ---")
violations = bval.validate_result(res1)
test("Nenhuma violacao para resultado padrao", len(violations) == 0)
test("is_safe retorna True", bval.is_safe(res1))

print()
print("--- Teste 5: BrainValidator - validate_context ---")
bad_ctx = OperationalBrainContext(
    timestamp="", symbol="", price=0,
    macro_trend="", top_down_status="", session="", killzone="",
    direction="", smc_state="", elliott_state="",
    fibonacci_context="", liquidity_context="",
    zone_id="", zone_type="", zone_timeframe="",
    touch_status="", structural_confirmation="",
)
warnings = bval.validate_context(bad_ctx)
test("Contexto invalido gera warnings", len(warnings) > 0)
good_ctx = ctx
warnings2 = bval.validate_context(good_ctx)
test("Contexto valido nao gera warnings", len(warnings2) == 0)

print()
print("--- Teste 6: MemoryStatus enum ---")
test("MemoryStatus tem VALIDATED", MemoryStatus.VALIDATED.value == "VALIDATED")
test("MemoryStatus tem REJECTED", MemoryStatus.REJECTED.value == "REJECTED")

print()
print("--- Teste 7: BrainConclusion enum ---")
test("BrainConclusion tem FAVORABLE", BrainConclusion.FAVORABLE.value == "FAVORAVEL")
test("BrainConclusion tem NO_EVIDENCE", BrainConclusion.NO_EVIDENCE.value == "SEM_EVIDENCIA")

print()
print("--- Teste 8: BrainEvidence criacao ---")
ev = BrainEvidence(
    evidence_id="EV001",
    evidence_type="memory",
    source_mcp="leon-memory",
    source_reference="REF001",
    status=MemoryStatus.VALIDATED,
    relevance=0.85,
    created_at="2026-07-24T10:00:00",
    summary="Contexto semelhante identificado"
)
test("Evidence id correto", ev.evidence_id == "EV001")
test("Evidence status VALIDATED", ev.status == MemoryStatus.VALIDATED)

print()
print("--- Teste 9: MCPStatus criacao ---")
mcp_st = MCPStatus(mcp_name="leon-market", available=True)
test("MCPStatus nome correto", mcp_st.mcp_name == "leon-market")
test("MCPStatus disponivel", mcp_st.available is True)

mcp_st2 = MCPStatus(mcp_name="leon-backtest", available=False, error="Timeout")
test("MCPStatus indisponivel com erro", mcp_st2.available is False)
test("MCPStatus erro registrado", mcp_st2.error == "Timeout")

print()
print("--- Teste 10: Brain desligado com shadow mode ---")
brain2 = LeonBrain()
ctx2 = OperationalBrainContext(
    timestamp="2026-07-24T12:00:00",
    symbol="XAUUSD",
    price=2510.50,
    macro_trend="BAIXA",
    top_down_status="ALINHADO",
    session="NEW_YORK",
    killzone="NY_OPEN",
    direction="VENDA",
    smc_state="CHOCH_CONFIRMADO",
    elliott_state="ONDA_C",
    fibonacci_context="EXTENSAO_127.2",
    liquidity_context="ABAIXO",
    zone_id="Z002",
    zone_type="FVG",
    zone_timeframe="M30",
    touch_status="SEM_TOQUE",
    structural_confirmation="PENDENTE",
)
result2 = brain2.process_context(ctx2)
test("Processamento com shadow nao quebra", result2 is not None)
test("Shadow mode preservado no resultado", result2.shadow_mode is True)

print()
print("========================================")
print(f"Resultado: {PASS}/{TOTAL} passaram, {FAIL} falharam")
print("========================================")

sys.exit(0 if FAIL == 0 else 1)
