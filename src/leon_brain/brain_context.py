from datetime import datetime
from typing import Optional

from .brain_models import OperationalBrainContext


def build_context(
    symbol: str = "XAUUSD",
    price: float = 0.0,
    macro_trend: str = "INDEFINIDA",
    top_down_status: str = "PENDENTE",
    session: str = "",
    killzone: str = "",
    direction: str = "NEUTRO",
    smc_state: str = "ANALISANDO",
    elliott_state: str = "ANALISANDO",
    fibonacci_context: str = "",
    liquidity_context: str = "",
    zone_id: str = "",
    zone_type: str = "",
    zone_timeframe: str = "",
    touch_status: str = "SEM_TOQUE",
    structural_confirmation: str = "PENDENTE",
    missing_confirmations: Optional[list[str]] = None,
    current_blockers: Optional[list[str]] = None,
    strategy_version: str = "",
    operation_id: str = "",
    source_snapshot_id: str = "",
) -> OperationalBrainContext:

    return OperationalBrainContext(
        timestamp=datetime.now().isoformat(timespec="seconds"),
        symbol=symbol,
        price=price,
        macro_trend=macro_trend,
        top_down_status=top_down_status,
        session=session,
        killzone=killzone,
        direction=direction,
        smc_state=smc_state,
        elliott_state=elliott_state,
        fibonacci_context=fibonacci_context,
        liquidity_context=liquidity_context,
        zone_id=zone_id,
        zone_type=zone_type,
        zone_timeframe=zone_timeframe,
        touch_status=touch_status,
        structural_confirmation=structural_confirmation,
        missing_confirmations=missing_confirmations or [],
        current_blockers=current_blockers or [],
        strategy_version=strategy_version,
        operation_id=operation_id,
        source_snapshot_id=source_snapshot_id,
    )


def context_to_dict(ctx: OperationalBrainContext) -> dict:
    return {
        "timestamp": ctx.timestamp,
        "symbol": ctx.symbol,
        "price": ctx.price,
        "macro_trend": ctx.macro_trend,
        "top_down_status": ctx.top_down_status,
        "session": ctx.session,
        "killzone": ctx.killzone,
        "direction": ctx.direction,
        "smc_state": ctx.smc_state,
        "elliott_state": ctx.elliott_state,
        "fibonacci_context": ctx.fibonacci_context,
        "liquidity_context": ctx.liquidity_context,
        "zone_id": ctx.zone_id,
        "zone_type": ctx.zone_type,
        "zone_timeframe": ctx.zone_timeframe,
        "touch_status": ctx.touch_status,
        "structural_confirmation": ctx.structural_confirmation,
        "missing_confirmations": ctx.missing_confirmations,
        "current_blockers": ctx.current_blockers,
        "strategy_version": ctx.strategy_version,
        "operation_id": ctx.operation_id,
        "source_snapshot_id": ctx.source_snapshot_id,
    }
