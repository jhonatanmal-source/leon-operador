#!/usr/bin/env python3
"""
MT5 Safe Wrapper — Redirect/alias to the canonical mt5_safe module.

This file exists only as a backward-compatibility redirect. The canonical
safe MT5 wrapper lives at /opt/leon/app/mt5_safe.py.

All public symbols are re-exported from the canonical module. New code
should import directly from mt5_safe:

    import mt5_safe as mt5

or:

    from mt5_safe import safe_symbol_info_tick, safe_account_info, ...
"""

import sys
import os
import types

# Ensure the project root is in sys.path so we can import mt5_safe
# File is at /opt/leon/app/src/mcp/_mt5_safe.py → root is two levels up
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Import the canonical module and re-export everything
import mt5_safe as _canonical  # noqa: E402

# Re-export all public names from the canonical module
__all__ = [name for name in dir(_canonical) if not name.startswith("_")]

# Module-level __getattr__ for transparent proxy (same pattern as canonical)
def __getattr__(name: str):
    return getattr(_canonical, name)


def __dir__() -> list[str]:
    return dir(_canonical)
