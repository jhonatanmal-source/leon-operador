import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.telegram_analysis_status import build_analysis_message


class FakeMT5:
    def symbol_info_tick(self, symbol):
        assert symbol == "Gold_Spot"
        return SimpleNamespace(bid=4088.63, ask=4088.99)

    def positions_get(self, *, symbol):
        assert symbol == "Gold_Spot"
        return (
            SimpleNamespace(profit=-18.82),
            SimpleNamespace(profit=-14.46),
            SimpleNamespace(profit=-7.66),
        )


def _write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def test_analysis_command_separates_official_view_from_lab(tmp_path):
    _write_csv(
        tmp_path / "brain_context_memory.csv",
        ["data", "preco", "direcao", "smc", "elliott", "alinhamento"],
        [{
            "data": "2026-07-27T01:49:47",
            "preco": "4089.89",
            "direcao": "AGUARDAR",
            "smc": "ALTA",
            "elliott": "POSSIVEL ONDA 3",
            "alinhamento": "CONFLITO",
        }],
    )
    _write_csv(
        tmp_path / "market_context_memory.csv",
        ["macro", "h4", "h1", "m15", "top_down_alinhamento"],
        [{
            "macro": "BAIXA",
            "h4": "BAIXA",
            "h1": "ALTA",
            "m15": "LATERAL",
            "top_down_alinhamento": "MISTO",
        }],
    )
    _write_csv(
        tmp_path / "pre_operation_trades.csv",
        [
            "id", "ativo", "context_mode", "region_id", "stop", "tp1", "tp2",
            "structural_gate_result", "cycle_id", "analysis_id",
        ],
        [{
            "id": "PREOP-000490",
            "ativo": "Gold_Spot",
            "context_mode": "BLOQUEADO",
            "region_id": "REG-1",
            "stop": "4085.06",
            "tp1": "4097.13",
            "tp2": "4104.38",
            "structural_gate_result": "PASSED",
            "cycle_id": "lab-cycle",
            "analysis_id": "lab-bootstrap",
        }],
    )
    _write_csv(
        tmp_path / "mt5_order_memory.csv",
        ["data", "status"],
        [
            {"data": "2026-07-27T00:05:09", "status": "ENVIADA"},
            {"data": "2026-07-27T00:10:15", "status": "ENVIADA"},
            {"data": "2026-07-27T00:15:24", "status": "ENVIADA"},
        ],
    )
    (tmp_path / "interest_zones.json").write_text(
        json.dumps([{
            "region_id": "REG-1",
            "zone_source": "LABORATORIO",
            "region_type": "DEMANDA",
            "region_low": 4085.06,
            "region_high": 4089.89,
            "invalidation_price": 4085.06,
            "target_prices": [4097.13, 4104.38],
        }]),
        encoding="utf-8",
    )

    message = build_analysis_message(
        tmp_path,
        mt5_module=FakeMT5(),
        now=datetime(2026, 7, 27, 2, 0),
    )

    assert "LEON VPS — ANÁLISE DO OPERADOR" in message
    assert "Macro: Venda" in message
    assert "H1: Compra" in message
    assert "M15: Lateral" in message
    assert "Decisão: AGUARDAR" in message
    assert "Laboratório / aprendizado — não oficial" in message
    assert "confirmação causal oficial não comprovada" in message
    assert "Limite diário DEMO atingido: 3/3" in message
    assert "Posições abertas: 3" in message
    assert "Resultado flutuante: -40,94" in message
    assert "PREOP-000490" in message
    assert "REG-1" in message


def test_analysis_command_survives_missing_optional_data(tmp_path):
    message = build_analysis_message(
        tmp_path,
        mt5_module=None,
        now=datetime(2026, 7, 27, 2, 0),
    )

    assert "LEON VPS — ANÁLISE DO OPERADOR" in message
    assert "Ainda não disponível" in message
    assert "Telegram não autoriza operações" in message
