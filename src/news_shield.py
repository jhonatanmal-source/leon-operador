import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
ENV_FILE = ROOT_DIR / ".env"
MANUAL_EVENTS_FILE = DATA_DIR / "news_events.json"
CACHE_FILE = DATA_DIR / "news_calendar_cache.json"

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
    return data if isinstance(data, list) else []


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
        return []
    CACHE_FILE.write_text(
        json.dumps(events, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return events


def _load_events():
    try:
        api_events = _api_events()
    except (requests.RequestException, ValueError):
        api_events = None

    if api_events is not None:
        return api_events, "TRADING_ECONOMICS"

    manual = _manual_events()
    if manual:
        return manual, "MANUAL"

    if CACHE_FILE.exists():
        try:
            cached = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if isinstance(cached, list):
                return cached, "CACHE"
        except (OSError, ValueError):
            pass

    return [], "NAO_CONFIGURADO"


def _is_relevant(event):
    importance = int(event.get("Importance") or event.get("importance") or 0)
    country = str(event.get("Country") or event.get("country") or "").lower()
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
        and any(term in name for term in HIGH_IMPACT_TERMS)
    )


def avaliar_news_shield(now=None, before_minutes=30, after_minutes=30):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    events, source = _load_events()
    relevant = []
    for event in events:
        if not _is_relevant(event):
            continue
        event_time = _parse_datetime(event.get("Date") or event.get("date"))
        if event_time is None:
            continue
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
