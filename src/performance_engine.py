from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
PRE_OPERATION_FILE = ROOT_DIR / "data" / "pre_operation_trades.csv"


def _ler_pre_operacao() -> list[dict[str, str]]:
    if not PRE_OPERATION_FILE.exists():
        return []
    with PRE_OPERATION_FILE.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _safe_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (ValueError, TypeError):
        return None


RESULTADOS_VALIDOS = {"WIN_TP1", "WIN_TP2", "LOSS", "BREAK_EVEN", "SEM_ENTRADA"}

METRIC_NOT_AVAILABLE = "NOT_AVAILABLE"
METRIC_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


def _r_multiplier(resultado: str, rr: float | None) -> float | None:
    if rr is None or rr <= 0:
        return None
    if resultado == "WIN_TP1":
        return 1.0 * rr
    if resultado == "WIN_TP2":
        return 2.0 * rr
    if resultado == "LOSS":
        return -1.0
    if resultado == "BREAK_EVEN" or resultado == "SEM_ENTRADA":
        return 0.0
    if resultado.startswith("WIN"):
        return rr
    return None


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except (ValueError, TypeError):
        return None


def analisar_performance(
    registros: list[dict[str, Any]] | None = None,
    origem: str | None = None,
) -> dict[str, Any]:
    if registros is None:
        registros = _ler_pre_operacao()

    if origem:
        filtrados = [r for r in registros if r.get("origin", "").strip().upper() == origem.upper()]
        total_registros_bruto = len(registros)
        registros = filtrados
    else:
        total_registros_bruto = len(registros)

    fechados = [r for r in registros if r.get("status") == "FECHADO"]
    abertos = [r for r in registros if r.get("status") == "ABERTO"]
    outros = [r for r in registros if r.get("status") not in ("FECHADO", "ABERTO", "OBSERVADO")]

    discarded: list[dict[str, Any]] = []
    valid_decididos: list[dict[str, Any]] = []

    for r in fechados:
        resultado = str(r.get("resultado", "")).strip()
        if not resultado:
            discarded.append({"id": r.get("id"), "reason": "NO_RESULT"})
            continue
        if resultado in ("NaN", "inf", "-inf", "nan"):
            discarded.append({"id": r.get("id"), "reason": f"INVALID_RESULT_VALUE_{resultado}"})
            continue
        if resultado not in RESULTADOS_VALIDOS and not resultado.startswith("WIN"):
            discarded.append({"id": r.get("id"), "reason": f"UNKNOWN_RESULT_{resultado}"})
            continue

        rr_raw = r.get("rr", "")
        rr = _safe_float(rr_raw)
        if rr_raw and rr is None:
            discarded.append({"id": r.get("id"), "reason": f"INVALID_RR_VALUE_{rr_raw}"})

        valid_decididos.append(r)

    wins = [r for r in valid_decididos if str(r.get("resultado", "")).startswith("WIN")]
    losses = [r for r in valid_decididos if r.get("resultado") == "LOSS"]
    breakeven = [r for r in valid_decididos if r.get("resultado") == "BREAK_EVEN"]

    r_values: list[float] = []
    for r in valid_decididos:
        rr = _safe_float(r.get("rr"))
        mult = _r_multiplier(r.get("resultado", ""), rr)
        if mult is not None:
            r_values.append(mult)

    timestamps = [
        _parse_timestamp(r.get("data_fechamento"))
        for r in valid_decididos
        if _parse_timestamp(r.get("data_fechamento"))
    ]
    sorted_timestamps = sorted(t for t in timestamps if t is not None)
    data_inicio = sorted_timestamps[0].isoformat() if sorted_timestamps else METRIC_NOT_AVAILABLE
    data_fim = sorted_timestamps[-1].isoformat() if sorted_timestamps else METRIC_NOT_AVAILABLE

    if not valid_decididos:
        return {
            "total_trades": 0,
            "total_decididos": 0,
            "total_com_r_valido": 0,
            "total_sem_r_valido": 0,
            "cobertura_r_percentual": METRIC_INSUFFICIENT_DATA,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "win_rate": METRIC_INSUFFICIENT_DATA,
            "loss_rate": METRIC_INSUFFICIENT_DATA,
            "ratio_win_loss": METRIC_INSUFFICIENT_DATA,
            "resultado_em_r": METRIC_INSUFFICIENT_DATA,
            "media_r": METRIC_INSUFFICIENT_DATA,
            "media_r_vencedores": METRIC_INSUFFICIENT_DATA,
            "media_r_perdedores": METRIC_INSUFFICIENT_DATA,
            "expectativa": METRIC_INSUFFICIENT_DATA,
            "profit_factor": METRIC_INSUFFICIENT_DATA,
            "drawdown_maximo": METRIC_INSUFFICIENT_DATA,
            "sequencia_maxima_ganhos": METRIC_INSUFFICIENT_DATA,
            "sequencia_maxima_perdas": METRIC_INSUFFICIENT_DATA,
            "resultado_por_direcao": {},
            "resultado_por_killzone": METRIC_NOT_AVAILABLE,
            "total_registros": total_registros_bruto,
            "total_abertos": len(abertos),
            "discarded": len(discarded),
            "discarded_details": discarded,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "origens": _coletar_origens(registros),
        }

    total_decididos = len(valid_decididos)
    win_rate = round((len(wins) / total_decididos) * 100, 2) if total_decididos > 0 else 0.0
    loss_rate = round((len(losses) / total_decididos) * 100, 2) if total_decididos > 0 else 0.0
    ratio_win_loss = (
        round(len(wins) / len(losses), 4)
        if losses and wins
        else (METRIC_INSUFFICIENT_DATA if not wins and not losses else METRIC_NOT_AVAILABLE)
    )

    resultado_em_r = round(sum(r_values), 2) if r_values else METRIC_INSUFFICIENT_DATA
    media_r = round(sum(r_values) / len(r_values), 2) if r_values else METRIC_INSUFFICIENT_DATA

    r_wins = [v for v in r_values if v > 0]
    r_losses = [v for v in r_values if v < 0]
    media_r_vencedores = round(sum(r_wins) / len(r_wins), 2) if r_wins else METRIC_INSUFFICIENT_DATA
    media_r_perdedores = round(abs(sum(r_losses)) / len(r_losses), 2) if r_losses else METRIC_INSUFFICIENT_DATA

    total_com_r_valido = len(r_values)
    total_sem_r_valido = total_decididos - total_com_r_valido
    cobertura_r_percentual = (
        round((total_com_r_valido / total_decididos) * 100, 2)
        if total_decididos > 0
        else METRIC_INSUFFICIENT_DATA
    )

    expectativa = (
        round(sum(r_values) / len(r_values), 4) if r_values else METRIC_INSUFFICIENT_DATA
    )

    gross_profit = sum(v for v in r_values if v > 0) if r_values else 0.0
    gross_loss = abs(sum(v for v in r_values if v < 0)) if r_values else 0.0
    if gross_loss > 0:
        profit_factor = round(gross_profit / gross_loss, 4)
    elif not r_values:
        profit_factor = METRIC_INSUFFICIENT_DATA
    elif gross_profit > 0:
        profit_factor = METRIC_NOT_AVAILABLE
    else:
        profit_factor = METRIC_INSUFFICIENT_DATA

    running = 0.0
    peak = 0.0
    max_dd = 0.0
    for v in r_values:
        running += v
        if running > peak:
            peak = running
        dd = peak - running
        if dd > max_dd:
            max_dd = dd
    drawdown_maximo = round(max_dd, 2) if r_values else METRIC_INSUFFICIENT_DATA

    max_win_streak = 0
    max_loss_streak = 0
    current_win_streak = 0
    current_loss_streak = 0
    for r in valid_decididos:
        res = r.get("resultado")
        if res == "LOSS":
            current_loss_streak += 1
            current_win_streak = 0
            if current_loss_streak > max_loss_streak:
                max_loss_streak = current_loss_streak
        elif str(res or "").startswith("WIN"):
            current_win_streak += 1
            current_loss_streak = 0
            if current_win_streak > max_win_streak:
                max_win_streak = current_win_streak
        else:
            current_win_streak = 0
            current_loss_streak = 0

    win_by_direction: dict[str, dict[str, int]] = {}
    for r in valid_decididos:
        direcao = r.get("direcao", "DESCONHECIDA")
        if direcao not in win_by_direction:
            win_by_direction[direcao] = {"total": 0, "wins": 0, "losses": 0}
        win_by_direction[direcao]["total"] += 1
        if str(r.get("resultado", "")).startswith("WIN"):
            win_by_direction[direcao]["wins"] += 1
        elif r.get("resultado") == "LOSS":
            win_by_direction[direcao]["losses"] += 1

    return {
        "total_trades": len(valid_decididos),
        "total_decididos": total_decididos,
        "total_com_r_valido": total_com_r_valido,
        "total_sem_r_valido": total_sem_r_valido,
        "cobertura_r_percentual": cobertura_r_percentual,
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(breakeven),
        "win_rate": win_rate,
        "loss_rate": loss_rate,
        "ratio_win_loss": ratio_win_loss,
        "resultado_em_r": resultado_em_r,
        "media_r": media_r,
        "media_r_vencedores": media_r_vencedores,
        "media_r_perdedores": media_r_perdedores,
        "expectativa": expectativa,
        "profit_factor": profit_factor,
        "drawdown_maximo": drawdown_maximo,
        "sequencia_maxima_ganhos": max_win_streak,
        "sequencia_maxima_perdas": max_loss_streak,
        "resultado_por_direcao": win_by_direction,
        "resultado_por_killzone": METRIC_NOT_AVAILABLE,
        "total_registros": total_registros_bruto,
        "total_abertos": len(abertos),
        "discarded": len(discarded),
        "discarded_details": discarded,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "origens": _coletar_origens(registros),
    }


def _coletar_origens(registros: list[dict[str, Any]]) -> dict[str, int]:
    origens: dict[str, int] = {}
    for r in registros:
        o = str(r.get("origin") or "").strip().upper()
        if not o:
            o = "UNKNOWN"
        origens[o] = origens.get(o, 0) + 1
    return origens
