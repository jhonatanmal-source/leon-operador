"""Entry through an already confirmed structural zone; FVG is a separate model."""
import math

from src.interest_zone_engine import InterestZoneStore, validate_zone_for_execution
from src.smc_price_levels import detect_swing_levels, MAX_TECHNICAL_RR


class StructuralEntryPlan(tuple):
    def __new__(cls, levels, region_id, model, evidence):
        obj = super().__new__(cls, levels)
        obj.region_id = region_id
        obj.model = model
        obj.evidence = evidence
        return obj


def _number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError):
        return None


def zone_retest_levels(zone, direction, m15, m5, min_rr):
    """Compute only after external canonical-zone validation. No synthetic targets."""
    buy = direction == 'COMPRA'
    allowed_types = {'BULLISH_ORDER_BLOCK', 'DEMAND_ZONE'} if buy else {'BEARISH_ORDER_BLOCK', 'SUPPLY_ZONE'}
    if direction not in ('COMPRA', 'VENDA') or zone.get('region_type') not in allowed_types:
        return None, 'ZONE_MODEL_OR_DIRECTION_MISMATCH'
    expected = 'BULLISH' if buy else 'BEARISH'
    if zone.get('region_direction') != expected:
        return None, 'ZONE_DIRECTION_MISMATCH'
    closed = m5[:-1]
    if len(closed) < 2 or len(m15) < 5:
        return None, 'INSUFFICIENT_CLOSED_BARS'
    candle = closed[-1]
    low, high = _number(zone.get('region_low')), _number(zone.get('region_high'))
    invalidation = _number(zone.get('invalidation_price'))
    if low is None or high is None or low >= high or invalidation is None:
        return None, 'ZONE_BOUNDS_OR_INVALIDATION_MISSING'
    if (buy and invalidation > low) or (not buy and invalidation < high):
        return None, 'INVALIDATION_INSIDE_ZONE'
    o,h,l,entry = [_number(candle.get(k)) for k in ('open','high','low','close')]
    if any(x is None for x in (o,h,l,entry)) or h <= l:
        return None, 'INVALID_REACTION_BAR'
    if l > high or h < low:
        return None, 'WAITING_ZONE_RETEST'
    if (buy and l <= invalidation) or (not buy and h >= invalidation):
        return None, 'ZONE_INVALIDATION_TOUCHED'
    reaction = entry > o and entry > (low+high)/2 if buy else entry < o and entry < (low+high)/2
    if not reaction:
        return None, 'WAITING_DIRECTIONAL_REACTION'
    # A reaction may leave the zone, but never chase beyond one zone width.
    if (buy and entry > high+(high-low)) or (not buy and entry < low-(high-low)):
        return None, 'REACTION_EXTENDED'
    stop = invalidation
    risk = entry-stop if buy else stop-entry
    if risk <= 0:
        return None, 'INVALID_TECHNICAL_STOP'
    highs,lows = detect_swing_levels(m15[:-1])
    targets = highs if buy else lows
    supplied = [_number(t) for t in zone.get('target_prices',[])]
    targets = sorted(set(targets + [t for t in supplied if t is not None]), reverse=not buy)
    targets = [t for t in targets if (t>entry if buy else t<entry)
               and float(min_rr) <= abs(t-entry)/risk <= MAX_TECHNICAL_RR]
    if len(targets) < 2:
        return None, 'INSUFFICIENT_TECHNICAL_TARGETS_AT_RR'
    levels = (round(entry,2), round(stop,2), round(targets[0],2),round(targets[1],2))
    actual_risk = abs(levels[0]-levels[1])
    if actual_risk <= 0 or abs(levels[3]-levels[0])/actual_risk < float(min_rr):
        return None, 'ROUNDED_LEVELS_INVALID'
    evidence = dict(zone_type=zone['region_type'],zone_low=low,zone_high=high,
                    invalidation_price=invalidation,retest_time=candle.get('time'),
                    retest_low=l,retest_high=h,reaction_close=entry,
                    source_event_id=zone.get('source_event_id'),
                    source_structure_id=zone.get('source_structure_id'),
                    source_module=zone.get('source_module'),
                    fvg_required=False)
    model = 'ORDER_BLOCK_RETEST' if 'ORDER_BLOCK' in zone['region_type'] else 'SUPPLY_DEMAND_RETEST'
    if zone.get('structure_model') == 'CHOCH_RETEST':
        model = 'CHOCH_ORDER_BLOCK_RETEST'
    return StructuralEntryPlan((*levels,round(abs(levels[3]-levels[0])/actual_risk,2)),
                               zone['region_id'],model,evidence), 'STRUCTURAL_ZONE_ENTRY_READY'


def confirmed_zone_entry(direction, symbol, m15, m5, min_rr, *, store=None):
    store = store or InterestZoneStore()
    reasons = []
    # Prefer recently updated existing zones, without inventing a zone to pass a guard.
    zones = sorted(store.list(),key=lambda z:str(z.get('updated_at','')),reverse=True)
    for zone in zones:
        if zone.get('zone_source') == 'LABORATORIO' or zone.get('replay_run_id'):
            continue
        if str(zone.get('symbol','')).upper() != str(symbol).upper() or zone.get('pre_operation_id'):
            continue
        if zone.get('region_type') not in {'BULLISH_ORDER_BLOCK','BEARISH_ORDER_BLOCK','DEMAND_ZONE','SUPPLY_ZONE'}:
            continue
        if zone.get('region_direction') != {'COMPRA':'BULLISH','VENDA':'BEARISH'}.get(direction):
            continue
        check = validate_zone_for_execution({'region_id':zone.get('region_id'),'ativo':symbol},store=store)
        if not check.get('ok'):
            reasons.append(check.get('error','ZONE_REJECTED'));continue
        plan, reason = zone_retest_levels(check['region'],direction,m15,m5,min_rr)
        if plan is not None:
            return plan, reason
        reasons.append(reason)
    return None, ','.join(sorted(set(reasons))) if reasons else 'NO_CONFIRMED_STRUCTURAL_ZONE'
