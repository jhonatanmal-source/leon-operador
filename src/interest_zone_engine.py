"""Canonical interest-zone contract and lifecycle for LEON.

This module consolidates market evidence produced by existing studies. It does not
calculate orders, approve risk, call OpenRouter, or communicate with MT5.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import threading
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ZONE_FILE = ROOT_DIR / "data" / "interest_zones.json"

REGION_TYPES = {
    "BULLISH_ORDER_BLOCK",
    "BEARISH_ORDER_BLOCK",
    "BULLISH_FVG",
    "BEARISH_FVG",
    "LIQUIDITY_BUY_SIDE",
    "LIQUIDITY_SELL_SIDE",
    "DEMAND_ZONE",
    "SUPPLY_ZONE",
    "PREMIUM_ZONE",
    "DISCOUNT_ZONE",
    "ELLIOTT_WAVE_C_ZONE",
    "FIB_RETRACEMENT_ZONE",
    "FIB_EXTENSION_ZONE",
    "COMPOSITE_INTEREST_ZONE",
}

EXECUTABLE_SMC_REGION_TYPES = {
    "BULLISH_ORDER_BLOCK", "BEARISH_ORDER_BLOCK", "BULLISH_FVG", "BEARISH_FVG",
    "LIQUIDITY_BUY_SIDE", "LIQUIDITY_SELL_SIDE", "DEMAND_ZONE", "SUPPLY_ZONE",
    "PREMIUM_ZONE", "DISCOUNT_ZONE", "COMPOSITE_INTEREST_ZONE",
}

REGION_STATES = {
    "IDENTIFICADA",
    "FORA_DA_ZONA",
    "APROXIMANDO",
    "TOCADA",
    "ATIVA",
    "AGUARDANDO_LIQUIDEZ",
    "LIQUIDEZ_TRABALHADA",
    "AGUARDANDO_ESTRUTURA",
    "AGUARDANDO_CONFIRMACAO",
    "CONFIRMADA",
    "INVALIDADA",
    "EXPIRADA",
    "CANCELADA",
    "CONSUMIDA",
}

TERMINAL_REGION_STATES = {"INVALIDADA", "EXPIRADA", "CANCELADA", "CONSUMIDA"}
EXECUTABLE_REGION_STATES = {"CONFIRMADA"}

PROVENANCE_VERSION = "1"
IMMUTABLE_PROVENANCE_FIELDS = {
    "zone_id",
    "created_at",
    "source_candle_timestamp",
    "source_timeframe",
    "source_event_id",
    "source_structure_id",
    "source_zone_type",
    "source_lower_price",
    "source_upper_price",
}

MONITORING_STATE_BY_REGION = {
    "IDENTIFICADA": "PLANNED_ZONE",
    "FORA_DA_ZONA": "FAR_FROM_ZONE",
    "APROXIMANDO": "ZONE_APPROACHING",
    "TOCADA": "ZONE_TOUCHED",
    "ATIVA": "ZONE_TOUCHED",
    "AGUARDANDO_LIQUIDEZ": "SETUP_FORMING",
    "LIQUIDEZ_TRABALHADA": "SETUP_FORMING",
    "AGUARDANDO_ESTRUTURA": "SETUP_FORMING",
    "AGUARDANDO_CONFIRMACAO": "SETUP_FORMING",
    "CONFIRMADA": "SETUP_VALID",
    "INVALIDADA": "SETUP_INVALIDATED",
    "EXPIRADA": "ZONE_EXPIRED",
    "CANCELADA": "SETUP_INVALIDATED",
    "CONSUMIDA": "EXECUTED",
}

STATE_MACHINE_BY_REGION = {
    "IDENTIFICADA": "PLANNED_ZONE",
    "FORA_DA_ZONA": "WAITING_FOR_REGION",
    "APROXIMANDO": "ZONE_APPROACHING",
    "TOCADA": "ZONE_TOUCHED",
    "ATIVA": "ZONE_TOUCHED",
    "AGUARDANDO_LIQUIDEZ": "SETUP_FORMING",
    "LIQUIDEZ_TRABALHADA": "SETUP_FORMING",
    "AGUARDANDO_ESTRUTURA": "SETUP_FORMING",
    "AGUARDANDO_CONFIRMACAO": "SETUP_FORMING",
    "CONFIRMADA": "SETUP_VALID",
    "INVALIDADA": "SETUP_INVALIDATED",
    "EXPIRADA": "ZONE_EXPIRED",
    "CANCELADA": "ENTRY_MISSED",
    "CONSUMIDA": "EXECUTED",
}

_STORE_LOCK = threading.RLock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().upper() in {"1", "TRUE", "SIM", "YES", "OK"}


def _as_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _direction(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"COMPRA", "BULLISH", "ALTA", "BUY"}:
        return "BULLISH"
    if text in {"VENDA", "BEARISH", "BAIXA", "SELL"}:
        return "BEARISH"
    return "NEUTRAL"


def _canonical_type(value: Any, direction: str, evidence: dict[str, Any]) -> str:
    text = str(value or "").strip().upper().replace(" ", "_")
    aliases = {
        "FVG_BULLISH": "BULLISH_FVG",
        "FVG_BEARISH": "BEARISH_FVG",
        "FVG": "BULLISH_FVG" if direction == "BULLISH" else "BEARISH_FVG",
        "DEMANDA": "DEMAND_ZONE",
        "OFERTA": "SUPPLY_ZONE",
        "ORDER_BLOCK": "BULLISH_ORDER_BLOCK" if direction == "BULLISH" else "BEARISH_ORDER_BLOCK",
    }
    canonical = aliases.get(text, text)
    present = [
        _as_bool(evidence.get("order_block_present")),
        _as_bool(evidence.get("fvg_present")),
        _as_bool(evidence.get("liquidity_present")),
        _as_bool(evidence.get("elliott_scenario_present")),
        _as_bool(evidence.get("fib_present")),
    ]
    if sum(present) > 1:
        return "COMPOSITE_INTEREST_ZONE"
    if canonical in REGION_TYPES:
        return canonical
    if _as_bool(evidence.get("fvg_present")):
        return "BULLISH_FVG" if direction == "BULLISH" else "BEARISH_FVG"
    if _as_bool(evidence.get("order_block_present")):
        return "BULLISH_ORDER_BLOCK" if direction == "BULLISH" else "BEARISH_ORDER_BLOCK"
    return "DEMAND_ZONE" if direction == "BULLISH" else "SUPPLY_ZONE"


def _region_id(symbol: str, region_type: str, direction: str, timeframe: str, low: float, high: float) -> str:
    identity = f"{symbol.upper()}|{region_type}|{direction}|{timeframe.upper()}|{low:.5f}|{high:.5f}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16].upper()
    return f"REG-{digest}"


@dataclass(frozen=True)
class ZoneProvenance:
    zone_id: str
    created_at: str
    source_candle_timestamp: str
    source_timeframe: str
    source_event_id: str | None
    source_structure_id: str | None
    source_zone_type: str
    lower_price: float
    upper_price: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def provenance_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _zone_provenance(zone: dict[str, Any]) -> ZoneProvenance | None:
    """Return provenance only when the immutable origin is fully available."""

    try:
        zone_id = str(zone.get("zone_id") or zone.get("region_id") or "").strip()
        created_at = str(zone.get("created_at") or "").strip()
        source_stamp = str(zone.get("source_candle_timestamp") or "").strip()
        source_timeframe = str(zone.get("source_timeframe") or "").strip().upper()
        source_zone_type = str(
            zone.get("source_zone_type") or zone.get("region_type") or ""
        ).strip().upper()
        lower = float(
            zone.get("source_lower_price", zone.get("region_low", zone.get("lower_price")))
        )
        upper = float(
            zone.get("source_upper_price", zone.get("region_high", zone.get("upper_price")))
        )
    except (TypeError, ValueError):
        return None
    if not all((zone_id, created_at, source_stamp, source_timeframe, source_zone_type)):
        return None
    return ZoneProvenance(
        zone_id=zone_id,
        created_at=created_at,
        source_candle_timestamp=source_stamp,
        source_timeframe=source_timeframe,
        source_event_id=(str(zone.get("source_event_id") or "").strip() or None),
        source_structure_id=(
            str(zone.get("source_structure_id") or "").strip() or None
        ),
        source_zone_type=source_zone_type,
        lower_price=lower,
        upper_price=upper,
    )


def attach_zone_provenance(zone: dict[str, Any]) -> dict[str, Any]:
    """Persist immutable provenance for newly built zones without guessing legacy data."""

    updated = dict(zone)
    provenance = _zone_provenance(updated)
    if provenance is None:
        updated.setdefault("provenance_version", "LEGACY")
        updated.setdefault("provenance_hash", "")
        updated.setdefault("provenance_status", "LEGACY_INCOMPLETE_CAUSAL_EVIDENCE")
        return updated
    updated.update(
        zone_id=provenance.zone_id,
        source_event_id=provenance.source_event_id,
        source_structure_id=provenance.source_structure_id,
        source_zone_type=provenance.source_zone_type,
        source_lower_price=provenance.lower_price,
        source_upper_price=provenance.upper_price,
        provenance_version=PROVENANCE_VERSION,
        provenance_hash=provenance.provenance_hash,
        provenance_status="PRESERVED",
    )
    return updated


@dataclass
class InterestZone:
    region_id: str
    cycle_id: str
    analysis_id: str
    symbol: str
    created_at: str
    updated_at: str
    source_candle_timestamp: str
    region_low: float
    region_high: float
    region_mid: float
    region_type: str
    region_direction: str
    source_timeframe: str
    source_module: str
    source_reason: str
    context_id: str = ""
    scenario_id: str = ""
    scenario_type: str = ""
    zone_reason: str = ""
    confluences: list[str] = field(default_factory=list)
    pre_operation_id: str = ""
    current_price: float | None = None
    distance_to_region: float | None = None
    distance_unit: str = "PRICE"
    invalidation_price: float | None = None
    monthly_context: Any = None
    weekly_context: Any = None
    daily_context: Any = None
    h4_context: Any = None
    h1_context: Any = None
    market_phase: Any = None
    directional_context: Any = None
    order_block_present: bool = False
    order_block_type: str = ""
    fvg_present: bool = False
    liquidity_present: bool = False
    liquidity_type: str = ""
    liquidity_swept: bool = False
    bos_present: bool = False
    choch_present: bool = False
    mss_present: bool = False
    displacement_present: bool = False
    mitigation_status: str = ""
    elliott_scenario_present: bool = False
    elliott_scenario_type: str = ""
    possible_wave_c: bool = False
    impulse_possible: bool = False
    correction_possible: bool = False
    elliott_invalidation: Any = None
    elliott_reason: str = ""
    fib_present: bool = False
    fib_retracement_level: Any = None
    fib_extension_level: Any = None
    fib_zone_aligned: bool = False
    fib_invalidation: Any = None
    region_status: str = "IDENTIFICADA"
    region_valid: bool = True
    region_invalidated: bool = False
    invalidation_reason: str = ""
    next_required_event: str = "MONITORAR_APROXIMACAO"
    monitoring_enabled: bool = True
    transition_reason: str = "Zona criada a partir de evidencia estrutural existente."
    event_history: list[dict[str, Any]] = field(default_factory=list)
    detected_price: float | None = None
    created_before_touch: bool = True
    touch_timestamp: str = ""
    target_prices: list[float] = field(default_factory=list)
    expected_confirmations: list[str] = field(default_factory=list)
    expires_at: str = ""
    monitoring_state: str = "PLANNED_ZONE"
    state_machine_state: str = "PLANNED_ZONE"
    valid_confirmations: list[dict[str, Any]] = field(default_factory=list)
    confirmation_history: list[dict[str, Any]] = field(default_factory=list)
    contrary_evidence: list[dict[str, Any]] = field(default_factory=list)
    invalidating_evidence: list[dict[str, Any]] = field(default_factory=list)
    move_extended: bool = False
    replay_run_id: str = ""
    invalidated_at: str = ""
    expired_at: str = ""
    confirmation_audit: list[dict[str, Any]] = field(default_factory=list)
    monitor_timeline: list[dict[str, Any]] = field(default_factory=list)
    zone_source: str = "SMC_STRUCTURAL_ZONE"
    smc_sources: list[str] = field(default_factory=list)
    elliott_assessment_id: str = ""
    elliott_influenced_zone: bool = False
    fibonacci_valid: bool = False
    fibonacci_levels: list[float] = field(default_factory=list)
    killzone_name: str = ""
    killzone_start: str = ""
    killzone_end: str = ""
    inside_killzone: bool = False
    near_killzone: bool = False
    session_context: str = ""
    structural_confirmations: list[dict[str, Any]] = field(default_factory=list)
    strategy_version: str = "1.0.0-diagnostic"
    configuration_hash: str = ""
    source_event_id: str | None = None
    source_structure_id: str | None = None
    source_zone_type: str = ""
    source_lower_price: float | None = None
    source_upper_price: float | None = None
    provenance_version: str = PROVENANCE_VERSION
    provenance_hash: str = ""

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["zone_id"] = self.region_id
        payload["lower_price"] = self.region_low
        payload["upper_price"] = self.region_high
        payload["direction"] = self.region_direction
        payload["active"] = self.region_valid and self.monitoring_enabled
        return payload


# The existing canonical region is also the planned-interest-zone contract. The
# alias avoids a second lifecycle implementation while exposing the requested
# domain name to integrations and tests.
PlannedInterestZone = InterestZone


def build_zone_from_context(
    identity: dict[str, Any],
    consolidated_context: dict[str, Any],
    *,
    current_price: Any = None,
    reject_retroactive: bool = False,
) -> dict[str, Any] | None:
    """Build a zone only when real bounded market evidence exists."""

    context = dict(consolidated_context or {})
    region = dict(context.get("region") or {})
    smc = dict(context.get("smc") or {})
    elliott = dict(context.get("elliott") or {})
    fibonacci = dict(context.get("fibonacci") or {})
    low = _as_float(region.get("region_low"))
    high = _as_float(region.get("region_high"))
    if low is None or high is None or high <= low:
        return None
    if not _as_bool(region.get("region_detected", True)):
        return None

    direction = _direction(
        region.get("region_direction")
        or smc.get("direction")
        or context.get("directional_context")
    )
    if direction == "NEUTRAL":
        return None

    raw_type = region.get("region_type")
    fvg_present = bool(raw_type) and "FVG" in str(raw_type).upper()
    order_block_present = bool(raw_type) and "ORDER_BLOCK" in str(raw_type).upper()
    order_block_status = str(
        region.get("order_block_status") or smc.get("order_block_status") or ""
    ).upper()
    order_block_valid = _as_bool(smc.get("order_block_valid")) or order_block_status == "VALIDATED_ORDER_BLOCK"
    evidence = {
        "order_block_present": (order_block_present and order_block_valid) or order_block_valid,
        "fvg_present": fvg_present or _as_bool(smc.get("fvg_valid")),
        "liquidity_present": _as_bool(smc.get("liquidity_identified")),
        "elliott_scenario_present": _as_bool(elliott.get("scenario_present")),
        "fib_present": _as_bool(fibonacci.get("valid")) and _as_bool(
            fibonacci.get("fib_region_present", True)
        ),
    }
    normalized_type = str(raw_type or "").strip().upper().replace(" ", "_")
    structural_zone_present = normalized_type in EXECUTABLE_SMC_REGION_TYPES or normalized_type in {
        "DEMANDA", "OFERTA", "ORDER_BLOCK", "FVG", "FVG_BULLISH", "FVG_BEARISH"
    }
    smc_structure_present = bool(
        evidence["order_block_present"]
        or evidence["fvg_present"]
        or evidence["liquidity_present"]
        or normalized_type in {
            "DEMAND_ZONE", "SUPPLY_ZONE", "PREMIUM_ZONE", "DISCOUNT_ZONE",
            "LIQUIDITY_BUY_SIDE", "LIQUIDITY_SELL_SIDE", "DEMANDA", "OFERTA",
        }
    )
    if normalized_type in {"ELLIOTT_WAVE_C_ZONE", "FIB_RETRACEMENT_ZONE", "FIB_EXTENSION_ZONE"} and not smc_structure_present:
        return None
    if order_block_present and not order_block_valid:
        return None
    if not smc_structure_present or not structural_zone_present:
        return None

    region_type = _canonical_type(raw_type, direction, evidence)
    timeframe = str(region.get("source_timeframe") or identity.get("timeframe") or "M15")
    symbol = str(identity.get("symbol") or context.get("symbol") or "").upper()
    if not symbol:
        return None
    now = _utc_now()
    price = _as_float(current_price)
    price_inside = price is not None and low <= price <= high
    already_reacted = _as_bool(
        region.get("already_reacted")
        or region.get("region_already_reacted")
        or context.get("region_already_reacted")
    )
    if reject_retroactive and (price_inside or already_reacted):
        return None
    invalidation = _as_float(region.get("invalidation_price"))
    if invalidation is None:
        invalidation = low if direction == "BULLISH" else high

    confluences = list(region.get("confluences") or context.get("zone_confluences") or [])
    for label, present in (
        ("ORDER_BLOCK", evidence["order_block_present"]),
        ("FVG", evidence["fvg_present"]),
        ("LIQUIDITY", evidence["liquidity_present"]),
        ("ELLIOTT", evidence["elliott_scenario_present"]),
        ("FIBONACCI", evidence["fib_present"]),
    ):
        if present and label not in confluences:
            confluences.append(label)
    source_reason = str(
        region.get("zone_reason")
        or region.get("source_reason")
        or (smc.get("reason") if isinstance(smc.get("reason"), str) else "")
        or "Evidencia estrutural delimitou faixa operacional."
    )

    zone = InterestZone(
        region_id=_region_id(symbol, region_type, direction, timeframe, low, high),
        cycle_id=str(identity.get("cycle_id") or context.get("cycle_id") or ""),
        analysis_id=str(identity.get("analysis_id") or context.get("analysis_id") or ""),
        pre_operation_id=str(identity.get("pre_operation_id") or ""),
        symbol=symbol,
        created_at=now,
        updated_at=now,
        source_candle_timestamp=str(
            identity.get("candle_timestamp") or context.get("candle_timestamp") or ""
        ),
        region_low=low,
        region_high=high,
        region_mid=(low + high) / 2,
        current_price=price,
        detected_price=price,
        created_before_touch=not price_inside,
        invalidation_price=invalidation,
        target_prices=[
            value for value in (
                _as_float(item) for item in (
                    region.get("target_prices")
                    or context.get("target_prices")
                    or []
                )
            ) if value is not None
        ],
        expected_confirmations=list(
            region.get("expected_confirmations")
            or ["LIQUIDITY_REACTION", "STRUCTURE_OR_DISPLACEMENT"]
        ),
        expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat(timespec="seconds"),
        region_type=region_type,
        region_direction=direction,
        source_timeframe=timeframe,
        source_module=str(region.get("source_module") or "institutional_analysis_engine"),
        source_reason=source_reason,
        source_event_id=str(
            region.get("source_event_id") or context.get("source_event_id") or ""
        ) or None,
        source_structure_id=str(
            region.get("source_structure_id")
            or context.get("source_structure_id")
            or ""
        ) or None,
        source_zone_type=str(raw_type or region_type).strip().upper(),
        source_lower_price=low,
        source_upper_price=high,
        context_id=str(
            region.get("context_id")
            or context.get("context_id")
            or ""
        ),
        scenario_id=str(region.get("scenario_id") or context.get("scenario_id") or ""),
        scenario_type=str(region.get("scenario_type") or context.get("scenario_type") or ""),
        zone_reason=source_reason,
        confluences=confluences,
        monthly_context=context.get("monthly_context"),
        weekly_context=context.get("weekly_context"),
        daily_context=context.get("daily_context"),
        h4_context=context.get("h4_structure"),
        h1_context=context.get("h1_structure"),
        market_phase=context.get("market_phase"),
        directional_context=context.get("directional_context"),
        order_block_present=evidence["order_block_present"],
        order_block_type=str(smc.get("order_block_type") or ""),
        fvg_present=evidence["fvg_present"],
        liquidity_present=evidence["liquidity_present"],
        liquidity_type=str(smc.get("liquidity_direction") or ""),
        liquidity_swept=_as_bool(smc.get("liquidity_swept")),
        bos_present=_as_bool(smc.get("bos")) and "SEM_BOS" not in str(smc.get("bos")),
        choch_present=_as_bool(smc.get("choch")) and "SEM_CHOCH" not in str(smc.get("choch")),
        mss_present=_as_bool(smc.get("mss_confirmed")),
        displacement_present=_as_bool(smc.get("displacement_present")),
        mitigation_status=str(smc.get("mitigation_status") or ""),
        elliott_scenario_present=evidence["elliott_scenario_present"],
        elliott_scenario_type=str(elliott.get("scenario_type") or ""),
        possible_wave_c=_as_bool(elliott.get("possible_wave_c")),
        impulse_possible=_as_bool(elliott.get("impulse_possible")),
        correction_possible=_as_bool(elliott.get("correction_possible")),
        elliott_invalidation=elliott.get("invalidation"),
        elliott_reason=str(elliott.get("reason") or ""),
        fib_present=evidence["fib_present"],
        fib_retracement_level=fibonacci.get("fib_level"),
        fib_extension_level=fibonacci.get("fib_extension_level"),
        fib_zone_aligned=_as_bool(fibonacci.get("fib_confluence")),
        fib_invalidation=fibonacci.get("invalidation"),
        zone_source=str(region.get("zone_source") or region_type),
        smc_sources=list(region.get("smc_sources") or [
            label for label, present in (
                ("ORDER_BLOCK", evidence["order_block_present"]),
                ("FVG", evidence["fvg_present"]),
                ("LIQUIDITY", evidence["liquidity_present"]),
                ("STRUCTURAL_ZONE", structural_zone_present),
            ) if present
        ]),
        elliott_assessment_id=str(
            elliott.get("assessment_id") or context.get("elliott_assessment_id") or ""
        ),
        elliott_influenced_zone=bool(
            elliott.get("influenced_zone") and smc_structure_present
        ),
        fibonacci_valid=evidence["fib_present"],
        fibonacci_levels=[
            value for value in (
                _as_float(fibonacci.get("retracement")),
                _as_float(fibonacci.get("projection")),
            ) if value is not None
        ],
        killzone_name=str(context.get("killzone_name") or ""),
        killzone_start=str(context.get("killzone_start") or ""),
        killzone_end=str(context.get("killzone_end") or ""),
        inside_killzone=_as_bool(context.get("inside_killzone")),
        near_killzone=_as_bool(context.get("near_killzone")),
        session_context=str(context.get("session_context") or ""),
        configuration_hash=str(context.get("configuration_hash") or ""),
    ).as_dict()
    zone = attach_zone_provenance(zone)
    zone["event_history"] = [{
        "event": "REGION_IDENTIFIED",
        "from_status": "",
        "to_status": "IDENTIFICADA",
        "reason": zone["transition_reason"],
        "next_required_event": zone["next_required_event"],
        "timestamp": zone["created_at"],
        "cycle_id": zone["cycle_id"],
        "analysis_id": zone["analysis_id"],
        "pre_operation_id": zone["pre_operation_id"],
    }]
    return monitor_zone(zone, current_price=price, evidence={})


def build_zones_from_context(
    identity: dict[str, Any],
    consolidated_context: dict[str, Any],
    *,
    current_price: Any = None,
    reject_retroactive: bool = True,
) -> list[dict[str, Any]]:
    """Build bounded planned regions without requiring a complete entry trigger."""

    context = dict(consolidated_context or {})
    raw_regions = list(context.get("regions") or [])
    if not raw_regions and context.get("region"):
        raw_regions = [dict(context.get("region") or {})]
    zones: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_region in raw_regions:
        region = dict(raw_region or {})
        local = dict(context)
        local["region"] = region
        local["directional_context"] = (
            region.get("region_direction")
            or region.get("direction")
            or context.get("directional_context")
        )
        smc = dict(context.get("smc") or {})
        smc["direction"] = local["directional_context"]
        local["smc"] = smc
        zone = build_zone_from_context(
            identity,
            local,
            current_price=current_price,
            reject_retroactive=reject_retroactive,
        )
        if zone is None or zone["region_id"] in seen:
            continue
        seen.add(zone["region_id"])
        zones.append(zone)
    return zones


def merge_persisted_zone(
    candidate: dict[str, Any],
    persisted: dict[str, Any] | None,
) -> dict[str, Any]:
    """Refresh context fields while preserving lifecycle and event identity."""

    if not persisted:
        return attach_zone_provenance(candidate)
    original = dict(persisted)
    existing = dict(original)
    tracking_fields = {
        key: existing.get(key)
        for key in (
            "created_at", "detected_price", "created_before_touch", "touch_timestamp",
            "pre_operation_id", "event_history", "valid_confirmations",
            "confirmation_history", "contrary_evidence", "invalidating_evidence",
            "confirmation_audit", "monitor_timeline", "region_status",
            "monitoring_state", "region_valid", "region_invalidated",
            "invalidation_reason", "monitoring_enabled", "invalidated_at", "expired_at",
            "expires_at", "move_extended",
            "context_id", "scenario_id", "scenario_type",
        )
    }
    mutation_events = list(original.get("provenance_events") or [])
    rejected: list[str] = []
    for field in IMMUTABLE_PROVENANCE_FIELDS:
        original_key = "region_id" if field == "zone_id" else field
        original_value = original.get(field, original.get(original_key))
        candidate_value = candidate.get(field, candidate.get(original_key))
        if (
            original_value not in {None, ""}
            and candidate_value not in {None, ""}
            and candidate_value != original_value
        ):
            rejected.append(field)
    existing.update(candidate)
    for field in IMMUTABLE_PROVENANCE_FIELDS:
        original_key = "region_id" if field == "zone_id" else field
        if field in original:
            existing[field] = original[field]
        elif original_key in original:
            existing[original_key] = original[original_key]
            if field == "zone_id":
                existing["zone_id"] = original[original_key]
    existing.update({key: value for key, value in tracking_fields.items() if value is not None})
    existing["provenance_version"] = original.get("provenance_version", "LEGACY")
    existing["provenance_hash"] = original.get("provenance_hash", "")
    if rejected:
        mutation_events.append({
            "event": "ZONE_PROVENANCE_MUTATION_REJECTED",
            "fields": sorted(rejected),
            "timestamp": candidate.get("updated_at") or original.get("updated_at") or "",
        })
        existing["provenance_status"] = "ZONE_PROVENANCE_MUTATION_REJECTED"
    else:
        existing["provenance_status"] = original.get("provenance_status", "PRESERVED")
    existing["provenance_events"] = mutation_events[-100:]
    return existing


def _distance(price: float, low: float, high: float) -> float:
    if low <= price <= high:
        return 0.0
    return low - price if price < low else price - high


def _event_name(status: str) -> str:
    return {
        "IDENTIFICADA": "REGION_IDENTIFIED",
        "APROXIMANDO": "REGION_APPROACHING",
        "TOCADA": "REGION_TOUCHED",
        "ATIVA": "REGION_ACTIVE",
        "AGUARDANDO_LIQUIDEZ": "REGION_LIQUIDITY_WAITING",
        "LIQUIDEZ_TRABALHADA": "REGION_LIQUIDITY_SWEPT",
        "AGUARDANDO_ESTRUTURA": "REGION_STRUCTURE_WAITING",
        "AGUARDANDO_CONFIRMACAO": "REGION_CONFIRMATION_WAITING",
        "CONFIRMADA": "REGION_CONFIRMED",
        "INVALIDADA": "REGION_INVALIDATED",
        "EXPIRADA": "REGION_EXPIRED",
        "CONSUMIDA": "REGION_CONSUMED",
    }.get(status, "REGION_UPDATED")


def monitor_zone(
    zone: dict[str, Any],
    *,
    current_price: Any,
    evidence: dict[str, Any] | None = None,
    now: datetime | None = None,
    max_age: timedelta = timedelta(days=7),
) -> dict[str, Any]:
    """Update price lifecycle; structured confirmation is applied separately."""

    updated = dict(zone)
    evidence = dict(evidence or {})
    previous = str(updated.get("region_status") or "IDENTIFICADA")
    if previous in TERMINAL_REGION_STATES:
        return updated

    clock = now or datetime.now(timezone.utc)
    low = _as_float(updated.get("region_low"))
    high = _as_float(updated.get("region_high"))
    price = _as_float(current_price)
    if low is None or high is None or high <= low:
        raise ValueError("Zona sem limites de preco validos")

    explicit_invalidation = _as_bool(evidence.get("region_invalidated"))
    invalidation_price = _as_float(updated.get("invalidation_price"))
    direction = _direction(updated.get("region_direction"))
    price_invalidated = (
        price is not None
        and invalidation_price is not None
        and ((direction == "BULLISH" and price < invalidation_price) or (direction == "BEARISH" and price > invalidation_price))
    )
    created_at = str(updated.get("created_at") or "")
    expired = False
    expires_at = str(updated.get("expires_at") or "")
    try:
        explicit_expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if explicit_expiry.tzinfo is None:
            explicit_expiry = explicit_expiry.replace(tzinfo=timezone.utc)
        expired = clock >= explicit_expiry
    except ValueError:
        pass
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        expired = expired or clock - created > max_age
    except ValueError:
        pass

    if explicit_invalidation or price_invalidated:
        status = "INVALIDADA"
        reason = str(evidence.get("invalidation_reason") or "Preco rompeu o limite de invalidacao da zona.")
        next_event = "AGUARDAR_NOVA_ZONA"
        updated["region_valid"] = False
        updated["region_invalidated"] = True
        updated["invalidation_reason"] = reason
        updated["monitoring_enabled"] = False
        updated["invalidated_at"] = clock.isoformat(timespec="seconds")
    elif expired:
        status = "EXPIRADA"
        reason = "Zona excedeu sua janela temporal de monitoramento."
        next_event = "REAVALIAR_CONTEXTO_MAIOR"
        updated["region_valid"] = False
        updated["monitoring_enabled"] = False
        updated["expired_at"] = clock.isoformat(timespec="seconds")
    elif price is None:
        status = "IDENTIFICADA"
        reason = "Zona identificada; aguardando preco atual para monitoramento."
        next_event = "RECEBER_PRECO_ATUAL"
    else:
        distance = _distance(price, low, high)
        updated["distance_to_region"] = distance
        inside = distance == 0
        touched = bool(str(updated.get("touch_timestamp") or "").strip())
        if not inside and touched:
            status = previous if previous in {
                "ATIVA", "AGUARDANDO_LIQUIDEZ", "LIQUIDEZ_TRABALHADA",
                "AGUARDANDO_ESTRUTURA", "AGUARDANDO_CONFIRMACAO", "CONFIRMADA",
            } else "AGUARDANDO_CONFIRMACAO"
            reason = "Monitoramento pos-toque permanece ativo durante a reacao da regiao."
            next_event = "MONITORAR_REACAO_E_CONFIRMACOES"
        elif not inside:
            width = high - low
            status = "APROXIMANDO" if distance <= width else "FORA_DA_ZONA"
            reason = "Preco se aproxima da faixa identificada." if status == "APROXIMANDO" else "Preco permanece fora da zona monitorada."
            next_event = "PRECO_ENTRAR_NA_ZONA"
        elif not evidence:
            status = "ATIVA"
            reason = "Preco esta dentro da zona; toque nao autoriza entrada."
            next_event = "ANALISAR_LIQUIDEZ"
        else:
            liquidity_present = _as_bool(evidence.get("liquidity_present", updated.get("liquidity_present")))
            liquidity_swept = _as_bool(evidence.get("liquidity_swept", updated.get("liquidity_swept")))
            structure_confirmed = any(
                _as_bool(evidence.get(key, updated.get(key)))
                for key in ("bos_present", "choch_present", "mss_present", "displacement_present")
            )
            trigger_confirmed = _as_bool(evidence.get("trigger_confirmed"))
            updated["liquidity_present"] = liquidity_present
            updated["liquidity_swept"] = liquidity_swept
            for key in ("bos_present", "choch_present", "mss_present", "displacement_present"):
                if key in evidence:
                    updated[key] = _as_bool(evidence[key])
            if not liquidity_present or not liquidity_swept:
                status = "AGUARDANDO_LIQUIDEZ"
                reason = "Preco na zona, mas a liquidez exigida ainda nao foi trabalhada."
                next_event = "CONFIRMAR_VARREDURA_DE_LIQUIDEZ"
            elif not structure_confirmed:
                status = "AGUARDANDO_ESTRUTURA"
                reason = "Liquidez trabalhada; estrutura ainda nao confirmou o cenario."
                next_event = "CONFIRMAR_BOS_CHOCH_OU_MSS"
            elif not trigger_confirmed:
                status = "AGUARDANDO_CONFIRMACAO"
                reason = "Zona e estrutura validas; falta o gatilho operacional."
                next_event = "CONFIRMAR_GATILHO_NO_TIMEFRAME_DE_ENTRADA"
            else:
                status = "CONFIRMADA"
                reason = "Zona, liquidez, estrutura e gatilho confirmados."
                next_event = "VALIDAR_PRE_TRADE_E_RISCO"

        if inside and not str(updated.get("touch_timestamp") or "").strip():
            updated["touch_timestamp"] = clock.isoformat(timespec="seconds")

    updated["current_price"] = price
    updated["region_status"] = status
    updated["monitoring_state"] = MONITORING_STATE_BY_REGION.get(status, status)
    updated["state_machine_state"] = STATE_MACHINE_BY_REGION.get(status, status)
    updated["transition_reason"] = reason
    updated["next_required_event"] = next_event
    updated["updated_at"] = clock.isoformat(timespec="seconds")
    history = list(updated.get("event_history") or [])
    if status != previous or not history:
        history.append({
            "event": _event_name(status),
            "from_status": previous,
            "to_status": status,
            "reason": reason,
            "next_required_event": next_event,
            "timestamp": updated["updated_at"],
            "cycle_id": updated.get("cycle_id", ""),
            "analysis_id": updated.get("analysis_id", ""),
            "pre_operation_id": updated.get("pre_operation_id", ""),
        })
    updated["event_history"] = history[-100:]
    return updated


def _snapshot_clock(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def classify_invalidation_timeline(
    *,
    confirmation_completed_at: Any,
    entry_window_open_at: Any,
    invalidation_at: Any,
    lower_timeframe_proof: bool = False,
) -> str:
    if not confirmation_completed_at or not entry_window_open_at or not invalidation_at:
        return "INCOMPLETE_INVALIDATION_EVIDENCE"
    try:
        completed = _snapshot_clock(confirmation_completed_at)
        opened = _snapshot_clock(entry_window_open_at)
        invalidated = _snapshot_clock(invalidation_at)
    except (TypeError, ValueError):
        return "INCOMPLETE_INVALIDATION_EVIDENCE"
    if invalidated < completed:
        return "CONFIRMATION_INVALIDATED"
    if invalidated == completed or invalidated == opened:
        return (
            "INVALIDATED_BEFORE_SIMULATION"
            if lower_timeframe_proof and completed <= opened <= invalidated
            else "UNRESOLVED_INTRABAR"
        )
    if completed <= opened < invalidated:
        return "INVALIDATED_BEFORE_SIMULATION"
    return "INVALID_SEQUENCE"


def monitor_touched_zone(
    *,
    zone: dict[str, Any],
    market_snapshot: dict[str, Any],
    previous_state: Any = None,
    existing_confirmations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Monitor a persisted zone candle by candle without requiring redetection."""

    try:
        from .context_decision import audit_entry_confirmations, assess_operational_setup
    except ImportError:
        from context_decision import audit_entry_confirmations, assess_operational_setup

    snapshot = dict(market_snapshot or {})
    candle = dict(snapshot.get("candle") or {})
    clock = _snapshot_clock(snapshot.get("timestamp") or candle.get("timestamp"))
    before_state = str(previous_state or zone.get("monitoring_state") or "PLANNED_ZONE")
    before_confirmations = list(
        existing_confirmations
        if existing_confirmations is not None
        else zone.get("confirmation_history") or []
    )
    current_price = candle.get("close", snapshot.get("current_price"))
    detected_events = list(snapshot.get("events_detected") or [])
    evidence = {
        "region_invalidated": bool(snapshot.get("region_invalidated")),
        "invalidation_reason": snapshot.get("invalidation_reason"),
        "trigger_confirmed": bool(detected_events),
    }
    max_age = snapshot.get("max_age")
    monitor_kwargs = {
        "current_price": current_price,
        "evidence": evidence,
        "now": clock,
    }
    if isinstance(max_age, timedelta):
        monitor_kwargs["max_age"] = max_age
    updated = monitor_zone(zone, **monitor_kwargs)
    if snapshot.get("move_extended") is not None:
        updated["move_extended_observed"] = bool(snapshot.get("move_extended"))
    updated["replay_run_id"] = str(
        snapshot.get("replay_run_id") or updated.get("replay_run_id") or ""
    )

    detected = list(snapshot.get("events_detected") or [])
    structural = list(
        snapshot.get("structural_confirmations")
        or updated.get("structural_confirmations")
        or []
    )
    updated["structural_confirmations"] = structural
    combined = before_confirmations + detected
    contract_mode = str(snapshot.get("contract_mode") or "LEGACY_PRODUCTION").upper()
    accepted, audit = audit_entry_confirmations(
        updated,
        combined,
        accept_legacy_simple=contract_mode == "LEGACY_PRODUCTION",
    )
    current_event_ids = {
        str(dict(item or {}).get("event_id") or dict(item or {}).get("confirmation_id") or "")
        for item in detected
    }
    current_audit = [item for item in audit if item.get("event_id") in current_event_ids]

    if accepted:
        completed_values = [
            _snapshot_clock(item.confirmation_completed_at)
            for item in accepted
            if item.confirmation_completed_at
        ]
        if completed_values:
            completed_at = min(completed_values)
            completed_text = completed_at.isoformat(timespec="seconds")
            updated.setdefault("confirmation_completed_at", completed_text)
            updated.setdefault("confirmation_state", "COMPLETE")
            updated.setdefault(
                "confirmation_resolution_source",
                accepted[0].confirmation_resolution_source,
            )
            updated.setdefault("structure_event_at", accepted[0].structure_event_at)
            updated.setdefault("sweep_at", accepted[0].sweep_at)
            updated.setdefault("displacement_at", accepted[0].displacement_at)
            updated.setdefault("retest_at", accepted[0].retest_at)
            updated.setdefault("defense_at", accepted[0].defense_at)
            updated.setdefault("continuation_at", accepted[0].continuation_at)
            if not updated.get("entry_window_created_at"):
                updated.update({
                    "entry_window_created_at": completed_text,
                    "entry_window_open_at": completed_text,
                    "entry_window_close_at": "",
                    "entry_window_source": "CONFIRMED_ZONE_BOUNDS",
                    "entry_window_lower": updated.get("region_low"),
                    "entry_window_upper": updated.get("region_high"),
                    "entry_window_status": "WAITING_FOR_ENTRY_OPPORTUNITY",
                    "price_at_window_open": current_price,
                })
            elif clock > completed_at and not updated.get("first_post_confirmation_observation_at"):
                observation_text = clock.isoformat(timespec="seconds")
                updated["first_post_confirmation_observation_at"] = observation_text
                updated["price_at_window_close"] = current_price
                low = _as_float(updated.get("entry_window_lower"))
                high = _as_float(updated.get("entry_window_upper"))
                price = _as_float(current_price)
                if low is not None and high is not None and price is not None and low <= price <= high:
                    updated["first_valid_entry_at"] = observation_text
                    updated["entry_window_status"] = "ENTRY_OPPORTUNITY_OBSERVED"

    terminal = str(updated.get("region_status") or "").upper() in {
        "INVALIDADA", "EXPIRADA", "CANCELADA", "CONSUMIDA"
    }
    if terminal and updated.get("confirmation_completed_at"):
        invalidation_at = str(updated.get("invalidated_at") or updated.get("updated_at") or "")
        updated["invalidation_at"] = invalidation_at
        updated["invalidation_price_observed"] = updated.get("invalidation_price")
        updated["price_at_invalidation"] = current_price
        updated["invalidation_temporal_state"] = classify_invalidation_timeline(
            confirmation_completed_at=updated.get("confirmation_completed_at"),
            entry_window_open_at=updated.get("entry_window_open_at"),
            invalidation_at=invalidation_at,
            lower_timeframe_proof=bool(snapshot.get("lower_timeframe_proof")),
        )
    touched = bool(str(updated.get("touch_timestamp") or "").strip())
    if touched and not terminal:
        assessment = assess_operational_setup(
            symbol=str(updated.get("symbol") or "XAUUSD"),
            direction=str(updated.get("region_direction") or ""),
            context_valid=bool(snapshot.get("context_valid", True)),
            zone=updated,
            confirmations=[item.as_dict() for item in accepted],
            contrary_evidence=list(snapshot.get("contrary_evidence") or []),
            invalidating_evidence=list(snapshot.get("invalidating_evidence") or []),
            hard_blocks=list(snapshot.get("hard_blocks") or []),
            move_extended=bool(snapshot.get("move_extended")),
            post_touch_active=True,
            contract_mode=contract_mode,
        )
        updated = apply_setup_assessment_to_zone(updated, assessment, now=clock)
        pending_states = [
            str(item.get("confirmation_state") or item.get("state") or "").upper()
            for item in structural
            if not bool(item.get("quality_valid"))
        ]
        if assessment.get("decision") == "SETUP_FORMING" and pending_states:
            latest_state = pending_states[-1]
            if latest_state in {
                "STRUCTURE_EVENT_DETECTED", "WAITING_FOR_RETEST", "RETEST_DETECTED",
                "WAITING_FOR_DEFENSE", "DEFENSE_CONFIRMED", "WAITING_FOR_CONTINUATION",
                "INCOMPLETE_EVIDENCE", "UNRESOLVED_INTRABAR", "INVALID_SEQUENCE",
                "INVALIDATED", "RETEST_IN_PROGRESS", "RETEST_CONFIRMED",
                "CONTINUATION_CONFIRMED", "RETEST_FAILED", "STRUCTURE_INVALIDATED",
            }:
                updated["structural_state"] = latest_state
                updated["state_machine_state"] = latest_state
    else:
        updated["valid_confirmations"] = [item.as_dict() for item in accepted]
        updated["confirmation_history"] = [item.as_dict() for item in accepted]

    previous_audit = list(updated.get("confirmation_audit") or [])
    known_audit = {
        (item.get("event_id"), item.get("status"), item.get("source_module"))
        for item in previous_audit
    }
    for item in current_audit:
        key = (item.get("event_id"), item.get("status"), item.get("source_module"))
        if key not in known_audit:
            previous_audit.append(item)
            known_audit.add(key)
    updated["confirmation_audit"] = previous_audit[-500:]

    low = _as_float(updated.get("region_low"))
    high = _as_float(updated.get("region_high"))
    price = _as_float(current_price)
    inside = bool(
        low is not None and high is not None and price is not None and low <= price <= high
    )
    accepted_ids = {
        item.get("event_id") for item in current_audit
        if item.get("status") == "CONFIRMATION_ACCEPTED"
    }
    timeline = list(updated.get("monitor_timeline") or [])
    if touched:
        candle_timestamp = candle.get("timestamp") or clock.isoformat(timespec="seconds")
        if isinstance(candle_timestamp, datetime):
            candle_timestamp = candle_timestamp.isoformat()
        timeline.append({
            "replay_run_id": updated.get("replay_run_id", ""),
            "zone_id": updated.get("region_id", ""),
            "candle": candle_timestamp,
            "timestamp": clock.isoformat(timespec="seconds"),
            "state_before": before_state,
            "price": price,
            "inside_zone": inside,
            "confirmations_before": len(before_confirmations),
            "events_detected": [dict(item).get("confirmation_type") for item in detected],
            "events_accepted": [
                dict(item).get("confirmation_type") for item in detected
                if str(dict(item).get("event_id") or dict(item).get("confirmation_id")) in accepted_ids
            ],
            "events_rejected": [
                {"event_id": item.get("event_id"), "type": item.get("confirmation_type"), "status": item.get("status")}
                for item in current_audit if item.get("status") != "CONFIRMATION_ACCEPTED"
            ],
            "detector_results": dict(snapshot.get("detector_results") or {}),
            "confirmations_after": len(updated.get("valid_confirmations") or []),
            "state_after": updated.get("monitoring_state"),
            "reason": updated.get("transition_reason"),
        })
    updated["monitor_timeline"] = timeline[-2000:]
    return updated


def apply_setup_assessment_to_zone(
    zone: dict[str, Any],
    assessment: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Apply the canonical setup assessment without changing risk or execution."""

    updated = dict(zone)
    previous = str(updated.get("region_status") or "IDENTIFICADA")
    decision = str(assessment.get("decision") or "NO_SETUP").upper()
    mapping = {
        "SETUP_FORMING": ("AGUARDANDO_CONFIRMACAO", "SETUP_FORMING", "AGUARDAR_RETESTE_OU_CONFIRMAR_ESTRUTURA"),
        "SETUP_VALID": ("CONFIRMADA", "SETUP_VALID", "VALIDAR_PRE_TRADE_E_RISCO"),
        "SETUP_VALID_HIGH_CONFIDENCE": ("CONFIRMADA", "SETUP_VALID_HIGH_CONFIDENCE", "VALIDAR_PRE_TRADE_E_RISCO"),
        "ENTRY_MISSED": ("CANCELADA", "ENTRY_MISSED", "AGUARDAR_NOVA_ZONA"),
        "SETUP_INVALIDATED": ("INVALIDADA", "SETUP_INVALIDATED", "AGUARDAR_NOVA_ZONA"),
        "BLOCKED": (previous, "BLOCKED", "REMOVER_BLOQUEIO_CRITICO"),
    }
    if decision not in mapping:
        return updated
    status, monitoring_state, next_event = mapping[decision]
    confirmations = list(assessment.get("valid_confirmations") or [])
    reasons = list(assessment.get("reasons") or [])
    reason = reasons[0] if reasons else f"Avaliacao contextual: {decision}."
    if decision == "SETUP_FORMING":
        reason = f"Zona tocada; {len(confirmations)} confirmacao(oes) estrutural(is) completa(s)."
    elif decision == "SETUP_VALID":
        reason = "Uma confirmacao estrutural completa pos-toque validou o setup."
    elif decision == "SETUP_VALID_HIGH_CONFIDENCE":
        reason = "Duas ou mais confirmacoes independentes; risco permanece inalterado."

    clock = now or datetime.now(timezone.utc)
    updated.update(
        region_status=status,
        monitoring_state=monitoring_state,
        state_machine_state=monitoring_state,
        next_required_event=next_event,
        transition_reason=reason,
        updated_at=clock.isoformat(timespec="seconds"),
        valid_confirmations=confirmations,
        contrary_evidence=list(assessment.get("contrary_evidence") or []),
        invalidating_evidence=list(assessment.get("invalidating_evidence") or []),
        move_extended=bool(assessment.get("move_extended")),
        entry_window_status=str(
            assessment.get("entry_window_status")
            or updated.get("entry_window_status")
            or "NOT_CREATED"
        ),
    )
    if status in TERMINAL_REGION_STATES:
        updated["region_valid"] = False
        updated["monitoring_enabled"] = False
    history = list(updated.get("event_history") or [])
    if status != previous or decision in {"SETUP_VALID", "SETUP_VALID_HIGH_CONFIDENCE", "ENTRY_MISSED"}:
        history.append({
            "event": _event_name(status) if decision != "ENTRY_MISSED" else "ENTRY_MISSED",
            "from_status": previous,
            "to_status": status,
            "monitoring_state": monitoring_state,
            "reason": reason,
            "next_required_event": next_event,
            "timestamp": updated["updated_at"],
            "cycle_id": updated.get("cycle_id", ""),
            "analysis_id": updated.get("analysis_id", ""),
            "pre_operation_id": updated.get("pre_operation_id", ""),
        })
    updated["event_history"] = history[-100:]
    updated["confirmation_history"] = list(updated.get("confirmation_history") or []) + [
        item for item in confirmations
        if item not in list(updated.get("confirmation_history") or [])
    ]
    updated["confirmation_history"] = updated["confirmation_history"][-100:]
    return updated


class InterestZoneStore:
    """Atomic local store for current and historical zone lifecycle."""

    def __init__(self, path: str | Path = DEFAULT_ZONE_FILE):
        self.path = Path(path)

    def list(self) -> list[dict[str, Any]]:
        with _STORE_LOCK:
            if not self.path.exists():
                return []
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return []
            return [dict(item) for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []

    def get(self, region_id: str) -> dict[str, Any] | None:
        return next((item for item in self.list() if item.get("region_id") == region_id), None)

    def upsert(self, zone: dict[str, Any]) -> dict[str, Any]:
        region_id = str(zone.get("region_id") or "")
        if not region_id:
            raise ValueError("region_id obrigatorio")
        with _STORE_LOCK:
            records = self.list()
            existing = next((item for item in records if item.get("region_id") == region_id), None)
            merged = merge_persisted_zone(zone, existing)
            # Store upsert is a lifecycle write, not a context refresh. Mutable
            # monitoring fields from the caller must advance while provenance
            # remains the original one.
            if existing:
                for key, value in zone.items():
                    if key not in IMMUTABLE_PROVENANCE_FIELDS and key not in {
                        "provenance_version", "provenance_hash", "provenance_events",
                        "provenance_status",
                    }:
                        merged[key] = value
            if existing:
                merged["created_at"] = existing.get("created_at") or zone.get("created_at")
                old_history = list(existing.get("event_history") or [])
                new_history = list(zone.get("event_history") or [])
                combined = old_history + [item for item in new_history if item not in old_history]
                merged["event_history"] = combined[-100:]
            else:
                records.append(merged)
            if existing:
                records = [merged if item.get("region_id") == region_id else item for item in records]
            self._write(records)
            return merged

    def associate_pre_operation(self, region_id: str, pre_operation_id: str) -> dict[str, Any] | None:
        zone = self.get(region_id)
        if zone is None:
            return None
        if zone.get("pre_operation_id") not in {None, "", pre_operation_id}:
            raise ValueError("Zona ja associada a outra PRE_OPERATION")
        zone["pre_operation_id"] = pre_operation_id
        zone["updated_at"] = _utc_now()
        return self.upsert(zone)

    def _write(self, records: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        try:
            temporary.write_text(
                json.dumps(records, ensure_ascii=True, indent=2, default=str),
                encoding="utf-8",
            )
            json.loads(temporary.read_text(encoding="utf-8"))
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                temporary.unlink(missing_ok=True)


def validate_zone_for_execution(
    pre_operation: dict[str, Any],
    *,
    store: InterestZoneStore | None = None,
) -> dict[str, Any]:
    """Read-only execution guard; no order or risk behavior lives here."""

    region_id = str(pre_operation.get("region_id") or "").strip()
    if not region_id:
        return {"ok": False, "error": "PRE_OPERATION_REGION_REQUIRED", "reason": "Nova PRE_OPERATION sem region_id canonico."}
    zone = (store or InterestZoneStore()).get(region_id)
    if zone is None:
        return {"ok": False, "error": "REGION_NOT_FOUND", "reason": "Regiao canonica nao encontrada."}
    if str(zone.get("symbol") or "").upper() != str(pre_operation.get("ativo") or "").upper():
        return {"ok": False, "error": "REGION_SYMBOL_MISMATCH", "reason": "Regiao e PRE_OPERATION usam simbolos diferentes."}
    associated = str(zone.get("pre_operation_id") or "")
    preop_id = str(pre_operation.get("pre_operation_id") or pre_operation.get("id") or "")
    if associated and associated != preop_id:
        return {"ok": False, "error": "REGION_PRE_OPERATION_ID_MISMATCH", "reason": "Regiao pertence a outra PRE_OPERATION."}
    if not _as_bool(zone.get("region_valid")) or _as_bool(zone.get("region_invalidated")):
        return {"ok": False, "error": "REGION_INVALIDATED", "reason": zone.get("invalidation_reason") or "Regiao invalida."}
    if zone.get("region_status") not in EXECUTABLE_REGION_STATES:
        return {"ok": False, "error": "REGION_NOT_CONFIRMED", "reason": f"Regiao em estado {zone.get('region_status')}; confirmacao obrigatoria."}
    try:
        from .live_operational_contract import evaluate_live_confirmation_gate
    except ImportError:
        from live_operational_contract import evaluate_live_confirmation_gate
    confirmation_gate = evaluate_live_confirmation_gate(zone)
    if not confirmation_gate["allowed"]:
        return {
            "ok": False,
            "error": "REGION_CAUSAL_CONFIRMATION_REQUIRED",
            "reason": confirmation_gate["reason"],
            "confirmation_gate": confirmation_gate,
        }
    return {"ok": True, "region": zone}
