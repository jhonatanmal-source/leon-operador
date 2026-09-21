"""Read-only Telegram view of the market analysis produced by the LEON operator."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _safe_text(value: Any, default: str = "Ainda não disponível") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _price(value: Any) -> str:
    try:
        return f"{float(value):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return "Ainda não disponível"


def _latest_csv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    latest: dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            if row:
                latest = dict(row)
    return latest


def _sent_today(path: Path, day: str) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            timestamp = _safe_text(row.get("data"), "")
            if timestamp.startswith(day) and row.get("status") == "ENVIADA":
                count += 1
    return count


def _load_zone(path: Path, region_id: str) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    zones = payload if isinstance(payload, list) else payload.get("zones", [])
    if not isinstance(zones, list):
        return {}
    for zone in reversed(zones):
        if region_id and zone.get("region_id") == region_id:
            return dict(zone)
    return dict(zones[-1]) if zones else {}


def _market_snapshot(mt5_module: Any, symbol: str) -> dict[str, Any]:
    if mt5_module is None:
        return {}
    snapshot: dict[str, Any] = {}
    try:
        tick = mt5_module.symbol_info_tick(symbol)
        if tick is not None:
            snapshot["bid"] = getattr(tick, "bid", None)
            snapshot["ask"] = getattr(tick, "ask", None)
    except Exception as exc:  # read-only integration failure must not break Telegram
        snapshot["tick_error"] = type(exc).__name__
    try:
        positions = mt5_module.positions_get(symbol=symbol) or ()
        snapshot["positions_count"] = len(positions)
        snapshot["positions_profit"] = sum(
            float(getattr(position, "profit", 0.0) or 0.0)
            for position in positions
        )
    except Exception as exc:  # read-only integration failure must not break Telegram
        snapshot["positions_error"] = type(exc).__name__
    return snapshot


def _display_direction(value: Any) -> str:
    normalized = _safe_text(value, "").upper()
    if normalized in {"ALTA", "BULLISH", "COMPRA", "BUY"}:
        return "Compra"
    if normalized in {"BAIXA", "BEARISH", "VENDA", "SELL"}:
        return "Venda"
    if normalized == "LATERAL":
        return "Lateral"
    return _safe_text(value)


def _distance_to_zone(price: Any, lower: Any, upper: Any) -> str:
    try:
        current = float(price)
        low = float(lower)
        high = float(upper)
    except (TypeError, ValueError):
        return "Ainda não disponível"
    if low <= current <= high:
        return "Preço dentro da região"
    distance = low - current if current < low else current - high
    return f"{distance:.2f} ({round(distance / 0.01):d} pontos)".replace(".", ",")


def build_analysis_message(
    data_dir: str | Path,
    *,
    mt5_module: Any = None,
    now: datetime | None = None,
) -> str:
    """Build a compact, read-only `/analise` response from current operator state."""
    data_path = Path(data_dir)
    now = now or datetime.now()
    brain = _latest_csv(data_path / "brain_context_memory.csv")
    context = _latest_csv(data_path / "market_context_memory.csv")
    preop = _latest_csv(data_path / "pre_operation_trades.csv")
    region_id = _safe_text(preop.get("region_id"), "")
    zone = _load_zone(data_path / "interest_zones.json", region_id)
    symbol = _safe_text(preop.get("ativo") or zone.get("symbol"), "Gold_Spot")
    market = _market_snapshot(mt5_module, symbol)
    current_price = market.get("bid", brain.get("preco"))
    sent_today = _sent_today(data_path / "mt5_order_memory.csv", now.date().isoformat())

    zone_source = _safe_text(zone.get("zone_source"), "Não identificada")
    is_lab = zone_source.upper() in {"LABORATORIO", "LABORATÓRIO"} or str(
        preop.get("analysis_id", "")
    ).lower().startswith("lab")
    zone_label = (
        "Laboratório / aprendizado — não oficial"
        if is_lab
        else zone_source
    )

    blockers: list[str] = []
    if _safe_text(context.get("top_down_alinhamento"), "").upper() != "ALINHADO":
        blockers.append("Top-down e M15 ainda não estão alinhados")
    if _safe_text(preop.get("context_mode"), "").upper() == "BLOQUEADO":
        blockers.append("Contexto operacional está bloqueado")
    if _safe_text(brain.get("direcao"), "").upper() == "AGUARDAR":
        blockers.append("Decisão oficial aguarda confirmação")
    if is_lab:
        blockers.append("Região atual pertence ao modo aprendizado")
    if sent_today >= 3:
        blockers.append(f"Limite diário DEMO atingido: {sent_today}/3")
    if not blockers:
        blockers.append("Nenhum bloqueio registrado no snapshot")

    confirmation = (
        "Hipótese de aprendizado; confirmação causal oficial não comprovada"
        if is_lab
        else _safe_text(preop.get("structural_gate_result"))
    )
    invalidation = zone.get("invalidation_price", preop.get("stop"))
    targets = zone.get("target_prices") or [preop.get("tp1"), preop.get("tp2")]
    target_1 = targets[0] if len(targets) > 0 else None
    target_2 = targets[1] if len(targets) > 1 else None
    blocker_lines = "\n".join(f"• {item}" for item in blockers)

    next_event = (
        "Confirmação causal com alinhamento M15"
        f"\n\nou\n\nRompimento de {_price(invalidation)}, invalidando a hipótese atual"
    )

    return (
        "🦁 LEON VPS — ANÁLISE DO OPERADOR\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 VISÃO OFICIAL\n\n"
        f"• Preço: {_price(current_price)}\n"
        f"• Macro: {_display_direction(context.get('macro'))}\n"
        f"• H4: {_display_direction(context.get('h4'))}\n"
        f"• H1: {_display_direction(context.get('h1'))}\n"
        f"• M15: {_display_direction(context.get('m15'))}\n"
        f"• SMC contextual: {_safe_text(brain.get('smc'))}\n"
        f"• Elliott contextual: {_safe_text(brain.get('elliott'))}\n"
        f"• Alinhamento: {_safe_text(brain.get('alinhamento'))}\n"
        f"• Decisão: {_safe_text(brain.get('direcao'))}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📍 REGIÃO EM OBSERVAÇÃO\n\n"
        f"• Origem: {zone_label}\n"
        f"• Tipo: {_safe_text(zone.get('region_type'))}\n"
        f"• Faixa: {_price(zone.get('region_low'))} → {_price(zone.get('region_high'))}\n"
        f"• Distância: {_distance_to_zone(current_price, zone.get('region_low'), zone.get('region_high'))}\n"
        f"• Invalidação: {_price(invalidation)}\n"
        f"• TP1 projetado: {_price(target_1)}\n"
        f"• TP2 projetado: {_price(target_2)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 CONFIRMAÇÃO E BLOQUEIOS\n\n"
        f"• Confirmação: {confirmation}\n"
        f"{blocker_lines}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ EXPOSIÇÃO DEMO\n\n"
        f"• Posições abertas: {market.get('positions_count', 'Ainda não disponível')}\n"
        f"• Resultado flutuante: {_price(market.get('positions_profit'))}\n"
        f"• Ordens enviadas hoje: {sent_today}/3\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎯 PRÓXIMO EVENTO\n\n"
        f"{next_event}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "ℹ️ IDENTIDADE\n\n"
        f"• PRE_OPERATION: {_safe_text(preop.get('id'))}\n"
        f"• Região: {_safe_text(region_id)}\n"
        f"• Ciclo: {_safe_text(preop.get('cycle_id'))}\n"
        f"• Análise: {_safe_text(preop.get('analysis_id'))}\n"
        f"• Atualização: {_safe_text(brain.get('data'))}\n\n"
        "Consulta informativa. Telegram não autoriza operações."
    )

