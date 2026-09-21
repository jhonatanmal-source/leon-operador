"""Persistent daily entry pause. Never closes or modifies positions."""

import json
import math
import os
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "daily_entry_guard.json"


def update_daily_state(previous, day, pnl, baseline, loss_percent=2.0, giveback_percent=50.0, closed_pnl=None, closed_peak=None, giveback_balance=None):
    if not all(math.isfinite(x) for x in (pnl, baseline, loss_percent, giveback_percent)) or baseline <= 0:
        raise ValueError("Invalid daily risk inputs")
    state = dict(previous) if previous.get("day") == day else {"day": day, "peak": 0.0, "reason": ""}
    gain_pnl = pnl if closed_pnl is None else closed_pnl
    if not math.isfinite(gain_pnl) or (closed_peak is not None and not math.isfinite(closed_peak)):
        raise ValueError("Invalid closed profit")
    if closed_pnl is not None and state.get("basis") != "closed":
        state["peak"] = 0.0
        if state["reason"] == "DAILY_PROFIT_GIVEBACK_REACHED":
            state["reason"] = ""
        state["basis"] = "closed"
    state["peak"] = max(float(state["peak"]), gain_pnl, closed_peak or 0.0, 0.0)
    day_balance = state.get("giveback_day_balance", baseline if giveback_balance is None else giveback_balance)
    if not math.isfinite(day_balance) or day_balance <= 0:
        raise ValueError("Invalid giveback day balance")
    state["giveback_day_balance"] = day_balance
    activation_amount = day_balance * 0.04
    # Migrate the former any-positive-profit rule without clearing daily stops.
    if state.get("giveback_policy") != "closed-above-4pct-v1":
        if state["reason"] == "DAILY_PROFIT_GIVEBACK_REACHED" and state["peak"] <= activation_amount:
            state["reason"] = ""
        state["giveback_policy"] = "closed-above-4pct-v1"
    state["giveback_activation_percent"] = 4.0
    state["giveback_activation_amount"] = activation_amount
    state["giveback_armed"] = state["peak"] > activation_amount
    if not state["reason"]:
        if pnl <= -baseline * loss_percent / 100:
            state["reason"] = "DAILY_STOP_REACHED"
        elif state["giveback_armed"] and gain_pnl <= state["peak"] * (1 - giveback_percent / 100):
            state["reason"] = "DAILY_PROFIT_GIVEBACK_REACHED"
    state["pnl"] = pnl
    state["closed_pnl"] = closed_pnl
    state["approved"] = not bool(state["reason"])
    return state


def evaluate_daily_entry_guard(account_key, day, pnl, baseline, loss_percent=2.0, closed_pnl=None, closed_peak=None, giveback_balance=None):
    import fcntl

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATE_FILE.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        states = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
        state = update_daily_state(states.get(account_key, {}), day, pnl, baseline, loss_percent,
                                   closed_pnl=closed_pnl, closed_peak=closed_peak,
                                   giveback_balance=giveback_balance)
        states[account_key] = state
        temporary = STATE_FILE.with_suffix(".tmp")
        with temporary.open("w") as output:
            json.dump(states, output, indent=2)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(STATE_FILE)
        return state
