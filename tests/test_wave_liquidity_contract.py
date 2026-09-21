import ast
from pathlib import Path

import pytest
from src.operational_evidence import wave_liquidity_confirmation, setup_decision


@pytest.mark.parametrize("label", ["ONDA 3", "ONDA 5", "ABC_ZIGZAG", "POSSIVEL ONDA 3"])
@pytest.mark.parametrize("direction,trend,bias", [("COMPRA", "ALTA", "BULLISH"), ("VENDA", "BAIXA", "BEARISH")])
def test_supported_entries_reach_decision(label, direction, trend, bias):
    elliott = dict(valid=True, entry_eligible=True, direction=trend, label=label,
                   fibonacci_setup={"valid": label in ("ONDA 3", "ONDA 5")})
    smc = dict(direction=bias, liquidity=dict(direction=bias, index=50))
    result = wave_liquidity_confirmation(direction, elliott, smc)
    assert result["approved"]
    assert setup_decision(direction, elliott, True, result["approved"], True)["approved"]
    assert not setup_decision(direction, elliott, False, result["approved"], True)["approved"]
    assert not setup_decision(direction, elliott, True, result["approved"], False)["approved"]


@pytest.mark.parametrize("change", ["context_only", "invalid", "opposite_wave", "no_sweep", "opposite_sweep", "no_index", "conflict", "no_direction"])
def test_rejects_incomplete_or_conflicting_context(change):
    elliott = dict(valid=True, entry_eligible=True, direction="ALTA")
    smc = dict(direction="BULLISH", liquidity=dict(direction="BULLISH", index=50))
    direction = "COMPRA"
    if change == "context_only": elliott["entry_eligible"] = False
    if change == "invalid": elliott["valid"] = False
    if change == "opposite_wave": elliott["direction"] = "BAIXA"
    if change == "no_sweep": smc["liquidity"] = {}
    if change == "opposite_sweep": smc["liquidity"]["direction"] = "BEARISH"
    if change == "no_index": smc["liquidity"].pop("index")
    if change == "conflict": smc["liquidity_conflict"] = True
    if change == "no_direction": direction = None
    assert not wave_liquidity_confirmation(direction, elliott, smc)["approved"]


def test_pipeline_uses_same_contract():
    tree = ast.parse((Path(__file__).parents[1] / "src/leon.py").read_text())
    assignments = [n for n in tree.body if isinstance(n, ast.Assign)]
    node = next(n for n in assignments if any(isinstance(t, ast.Name) and t.id == "setup_onda_confirmado" for t in n.targets))
    assert ast.unparse(node.value) == "confirmacao_onda['approved']"
