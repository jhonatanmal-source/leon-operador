import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
ENV_FILE = ROOT_DIR / ".env"
MANUAL_EVENTS_FILE = DATA_DIR / "news_events.json"
CACHE_FILE = DATA_DIR / "news_calendar_cache.json"
FF_CACHE_FILE = DATA_DIR / "news_forexfactory_cache.json"

load_dotenv(ENV_FILE)

HIGH_IMPACT_TERMS = {
    "non farm payroll",
    "nonfarm payroll",
    "nfp",
    "fomc",
    "fed interest rate",
    "interest rate decision",
    "cpi",
    "consumer price",
    "pce",
    "gdp",
    "unemployment rate",
    "initial jobless claims",
    "retail sales",
}


def _parse_datetime(value):
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _manual_events():
    if not MANUAL_EVENTS_FILE.exists():
        return []
    try:
        data = json.loads(MANUAL_EVENTS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return _covered_events(data) or []


def _covered_events(data):
    if not isinstance(data, dict) or not isinstance(data.get("events"), list):
        return None
    start = _parse_datetime(data.get("valid_from"))
    end = _parse_datetime(data.get("valid_until"))
    now = datetime.now(timezone.utc)
    if start is None or end is None or not (start <= now - timedelta(minutes=30)
                                            and end >= now + timedelta(minutes=30)):
        return None
    return data["events"]


def _api_events():
    api_key = os.getenv("TRADING_ECONOMICS_API_KEY", "").strip()
    if not api_key:
        return None

    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=1)).date().isoformat()
    end = (now + timedelta(days=2)).date().isoformat()
    url = (
        "https://api.tradingeconomics.com/calendar/country/"
        f"united%20states/{start}/{end}?c={api_key}&importance=3"
    )
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    events = response.json()
    if not isinstance(events, list):
        raise ValueError("Invalid economic calendar response")
    CACHE_FILE.write_text(
        json.dumps({"events": events, "valid_from": start + "T00:00:00Z",
                    "valid_until": end + "T23:59:59Z"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return events


def _fresh_file(path, now):
    try:
        age = now.timestamp() - path.stat().st_mtime
        return 0 <= age <= 6 * 3600
    except OSError:
        return False


def _load_events():
    if os.getenv("LEON_NEWS_SOURCE") == "forex_factory":
        try:
            return _forex_factory_events(), "FOREX_FACTORY"
        except (requests.RequestException, OSError, ValueError, TypeError, KeyError):
            return [], "NAO_CONFIGURADO"
    try:
        api_events = _api_events()
    except (requests.RequestException, ValueError):
        api_events = None

    if api_events is not None:
        return api_events, "TRADING_ECONOMICS"

    now = datetime.now(timezone.utc)
    manual = _manual_events()
    if manual and _fresh_file(MANUAL_EVENTS_FILE, now):
        return manual, "MANUAL"

    if _fresh_file(CACHE_FILE, now):
        try:
            cached = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            events = _covered_events(cached)
            if events is not None:
                return events, "CACHE"
        except (OSError, ValueError):
            pass

    return [], "NAO_CONFIGURADO"


def _forex_factory_events():
    now = datetime.now(timezone.utc)
    if _fresh_file(FF_CACHE_FILE, now) and now.timestamp() - FF_CACHE_FILE.stat().st_mtime < 3600:
        events = _covered_events(json.loads(FF_CACHE_FILE.read_text(encoding="utf-8")))
        if events is not None:
            return events
    response = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=15)
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list) or not rows:
        raise ValueError("Empty weekly calendar")
    local = now.astimezone(ZoneInfo("America/New_York"))
    start = (local - timedelta(days=(local.weekday() + 1) % 7)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    events = []
    impacts = {"High": 3, "Medium": 2, "Low": 1, "Holiday": 1, "Non-Economic": 1}
    for row in rows:
        when = _parse_datetime(row["date"])
        if when is None or not start <= when < end:
            raise ValueError("Calendar week mismatch")
        if row["country"] == "USD":
            events.append({"Date": when.isoformat(), "Importance": impacts[row["impact"]],
                           "Country": "United States", "Event": row["title"]})
    envelope = {"events": events, "valid_from": start.isoformat(), "valid_until": end.isoformat()}
    if _covered_events(envelope) is None:
        raise ValueError("Calendar does not cover full blocking window")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FF_CACHE_FILE.write_text(json.dumps(envelope), encoding="utf-8")
    return events


def _is_relevant(event):
    importance = int(event.get("Importance") or event.get("importance") or 0)
    country = str(event.get("Country") or event.get("country") or "").lower()
    if importance not in (1, 2, 3) or not country or _parse_datetime(event.get("Date") or event.get("date")) is None:
        raise ValueError("Invalid calendar event")
    name = str(
        event.get("Event")
        or event.get("event")
        or event.get("Category")
        or event.get("category")
        or ""
    ).lower()
    return (
        importance >= 3
        and country in {"united states", "estados unidos", "usa", "us"}
    )


def avaliar_news_shield(now=None, before_minutes=30, after_minutes=30):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    events, source = _load_events()
    if source == "NAO_CONFIGURADO":
        return {"ok": False, "approved": False, "source": source,
                "reason": "NEWS_CALENDAR_UNAVAILABLE_OR_STALE",
                "blocking_events": [], "next_events": []}
    relevant = []
    for event in events:
        try:
            is_relevant = _is_relevant(event)
        except (AttributeError, TypeError, ValueError):
            return {"ok": False, "approved": False, "source": source,
                    "reason": "NEWS_CALENDAR_INVALID", "blocking_events": [], "next_events": []}
        if not is_relevant:
            continue
        event_time = _parse_datetime(event.get("Date") or event.get("date"))
        if event_time is None:
            return {"ok": False, "approved": False, "source": source,
                    "reason": "NEWS_CALENDAR_INVALID", "blocking_events": [], "next_events": []}
        relevant.append(
            {
                "name": event.get("Event") or event.get("event"),
                "time": event_time.isoformat(),
                "minutes_until": round(
                    (event_time - now).total_seconds() / 60,
                    1,
                ),
            }
        )

    blocking = [
        event
        for event in relevant
        if -after_minutes <= event["minutes_until"] <= before_minutes
    ]
    next_events = sorted(
        [event for event in relevant if event["minutes_until"] > 0],
        key=lambda event: event["minutes_until"],
    )[:5]

    return {
        "ok": True,
        "approved": not blocking,
        "source": source,
        "blocking_events": blocking,
        "next_events": next_events,
        "before_minutes": before_minutes,
        "after_minutes": after_minutes,
        "reason": (
            "HIGH_IMPACT_NEWS_WINDOW"
            if blocking
            else "NO_HIGH_IMPACT_NEWS_WINDOW"
        ),
        "warning": (
            "Calendario economico nao configurado."
            if source == "NAO_CONFIGURADO"
            else None
        ),
    }


def verificar_noticias():
    result = avaliar_news_shield()
    print("===================================")
    print("NEWS SHIELD")
    print("===================================")
    print(f"Fonte: {result['source']}")
    print(f"Operacao permitida: {result['approved']}")
    print(f"Motivo: {result['reason']}")
    return result
