"""Read-only FTMO entry guard. Unknown profile or account data blocks entries.

Rules source: https://ftmo.com/en/trading-objectives/ (2026-09-30).
This guards admission of new trades; it cannot guarantee fills or compliance.
"""
import configparser
import math
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.paths import BASE_DIR

CONFIG_FILE = BASE_DIR / "config.ini"
PROFILES = {"free_trial_1_step": 3.0, "free_trial_2_step": 5.0}


def blocked(reason):
    return {"ok": False, "approved": False, "reason": reason}


def evaluate_limits(profile, initial, day_balance, midnight_peak, equity,
                    reserved_risk=0, buffer_percent=0.1):
    if profile not in PROFILES:
        return blocked("FTMO_PROFILE_UNCONFIRMED")
    values = [initial, day_balance, midnight_peak, equity, reserved_risk, buffer_percent]
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        return blocked("FTMO_INVALID_NUMBERS")
    if min(initial, day_balance, midnight_peak, equity) <= 0 or reserved_risk < 0 or buffer_percent < 0.1:
        return blocked("FTMO_INVALID_NUMBERS")
    daily_floor = day_balance - initial * PROFILES[profile] / 100
    total_base = max(initial, midnight_peak) if profile == "free_trial_1_step" else initial
    total_floor = total_base - initial * 0.10
    # Internal daily stop is deliberately tighter than either FTMO product.
    internal_floor = day_balance - initial * 0.02
    projected = equity - reserved_risk - initial * buffer_percent / 100
    approved = projected > max(daily_floor, total_floor, internal_floor)
    return {"ok": True, "approved": approved,
            "reason": "FTMO_ENTRY_BUDGET_OK" if approved else "FTMO_LOSS_BUDGET_BLOCKED",
            "daily_floor": daily_floor, "total_floor": total_floor,
            "internal_daily_floor": internal_floor, "projected_equity": projected}


def ledger_state(deals, initial, balance, now):
    """Reconcile full broker history and reconstruct Prague midnight balances."""
    if deals is None:
        raise ValueError("FTMO_HISTORY_UNAVAILABLE")
    today = now.astimezone(ZoneInfo("Europe/Prague")).date()
    pnl_by_day = defaultdict(float)
    entries = set()
    deposit_seen = False
    activity_seen = False
    for d in sorted(deals, key=lambda item: item.time):
        net = sum(float(getattr(d, key)) for key in ("profit", "commission", "swap", "fee"))
        if not math.isfinite(net):
            raise ValueError("FTMO_INVALID_HISTORY")
        # MT5 DEAL_TYPE_BALANCE=2. Only one initial deposit is recognized.
        if d.type == 2:
            if deposit_seen or activity_seen or abs(net - initial) > 0.01:
                raise ValueError("FTMO_BALANCE_ADJUSTMENT_REVIEW_REQUIRED")
            deposit_seen = True
            continue
        if d.type not in (0, 1):
            raise ValueError("FTMO_UNSUPPORTED_LEDGER_ENTRY")
        activity_seen = True
        day = datetime.fromtimestamp(d.time, timezone.utc).astimezone(ZoneInfo("Europe/Prague")).date()
        if day > today or d.time > now.timestamp() + 5:
            raise ValueError("FTMO_FUTURE_HISTORY")
        pnl_by_day[day] += net
        if day == today and d.entry in (0, 2):
            entries.add(d.order)
    if not deposit_seen:
        raise ValueError("FTMO_INITIAL_DEPOSIT_HISTORY_REQUIRED")
    if abs(initial + sum(pnl_by_day.values()) - balance) > 0.02:
        raise ValueError("FTMO_HISTORY_BALANCE_MISMATCH")
    day_balance = initial
    peak = initial
    for day in sorted(pnl_by_day):
        if day < today:
            day_balance += pnl_by_day[day]
            peak = max(peak, day_balance)
    return day_balance, peak, len(entries)


def evaluate_ftmo_entry(mt5, request=None, expected_login=None):
    """Use an already-connected MT5 session; never login, send, or close trades."""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")
    profile = config.get("FTMO", "profile", fallback="pending")
    if profile not in PROFILES:
        return blocked("FTMO_PROFILE_UNCONFIRMED")
    try:
        initial = config.getfloat("FTMO", "initial_balance")
        login = config.getint("FTMO", "account_login")
        server = config.get("FTMO", "account_server")
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if account is None or terminal is None:
            return blocked("FTMO_ACCOUNT_UNAVAILABLE")
        if account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            return blocked("MT5_REAL_ACCOUNT_BLOCKED")
        if account.login != login or account.server != server or (expected_login is not None and account.login != expected_login):
            return blocked("FTMO_ACCOUNT_CHANGED")
        if not (account.trade_allowed and account.trade_expert and terminal.trade_allowed) or terminal.tradeapi_disabled:
            return blocked("MT5_ALGO_TRADING_DISABLED")
        now = datetime.now(timezone.utc)
        history = mt5.history_deals_get(datetime(1970, 1, 1, tzinfo=timezone.utc), now)
        day_balance, peak, entries = ledger_state(history, initial, float(account.balance), now)
        positions = mt5.positions_get()
        orders = mt5.orders_get()
        if positions is None or orders is None:
            return blocked("FTMO_EXPOSURE_UNAVAILABLE")
        if orders:
            return blocked("FTMO_PENDING_ORDERS_REVIEW_REQUIRED")
        if entries >= 3:
            return blocked("FTMO_INTERNAL_THREE_TRADES_LIMIT")
        reserved = 0.0
        for p in positions:
            if p.sl <= 0:
                return blocked("FTMO_POSITION_WITHOUT_SL")
            tick = mt5.symbol_info_tick(p.symbol)
            if tick is None or not 0 <= now.timestamp() - tick.time <= 120:
                return blocked("FTMO_STALE_TICK")
            price = tick.bid if p.type == mt5.ORDER_TYPE_BUY else tick.ask
            loss = mt5.order_calc_profit(p.type, p.symbol, p.volume, price, p.sl)
            if loss is None or not math.isfinite(loss):
                return blocked("FTMO_RISK_CALCULATION_UNAVAILABLE")
            reserved += max(0, -loss)
        if request:
            tick = mt5.symbol_info_tick(request["symbol"])
            if tick is None or not 0 <= now.timestamp() - tick.time <= 120:
                return blocked("FTMO_STALE_TICK")
            if request["sl"] <= 0 or request["tp"] <= 0:
                return blocked("FTMO_REQUEST_WITHOUT_SL_TP")
            loss = mt5.order_calc_profit(request["type"], request["symbol"], request["volume"], request["price"], request["sl"])
            if loss is None or not math.isfinite(loss) or loss >= 0:
                return blocked("FTMO_RISK_CALCULATION_UNAVAILABLE")
            reserved += -loss
        result = evaluate_limits(profile, initial, day_balance, peak, float(account.equity), reserved)
        # Reserve against the next Prague reset too: do not spend today's closed profits
        # on positions whose stops would exceed the next day's loss allowance.
        if result.get("approved") and result["projected_equity"] <= float(account.balance) - initial * .02:
            return blocked("FTMO_ROLLOVER_RISK_BUDGET_BLOCKED")
        return result
    except (AttributeError, KeyError, TypeError, ValueError, configparser.Error) as error:
        return blocked(str(error) if isinstance(error, ValueError) else "FTMO_PREFLIGHT_DATA_INVALID")
