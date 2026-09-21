import os
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"


def _source_safe(name: str) -> str:
    path = SRC / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def test_telegram_config_module_exists():
    source = _source_safe("telegram_config.py")
    assert "TOKEN" in source
    assert "CHAT_ID" in source
    assert "TELEGRAM_ENABLED" in source


def test_telegram_config_no_secrets_in_source():
    source = _source_safe("telegram_config.py")
    actual_token = os.getenv("LEON_TELEGRAM_TOKEN") or os.getenv("TELEGRAM_TOKEN")
    if actual_token:
        assert actual_token not in source


def test_telegram_config_loads_safely():
    from src import telegram_config
    assert hasattr(telegram_config, "TOKEN")
    assert hasattr(telegram_config, "CHAT_ID")
    assert hasattr(telegram_config, "TELEGRAM_ENABLED")


def test_telegram_source_no_order_send():
    source = _source_safe("telegram_config.py")
    assert "order_send" not in source
