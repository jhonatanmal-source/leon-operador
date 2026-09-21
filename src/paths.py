# ===================================
# PATHS — canonical path resolution
# ===================================
#
# All LEON modules should use this helper instead of
# hardcoded "C:/XAU_ELITE_AI/" paths.
#
# Usage:
#   from paths import BASE_DIR, DATA_DIR, REPORTS_DIR, LOGS_DIR
#   arquivo = DATA_DIR / "brain_memory.csv"
#
# ===================================

from pathlib import Path

# ── base: /opt/leon/app ──────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── well-known subdirectories ────────────────────────────────
DATA_DIR    = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR    = BASE_DIR / "logs"
SCREENSHOTS_DIR = BASE_DIR / "reports" / "trade_snapshots"

# ── ensure they exist at import time ─────────────────────────
for _dir in (DATA_DIR, REPORTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


def old_win_path(win_path: str) -> Path:
    """Convert a C:/XAU_ELITE_AI/... string to the real Linux Path.

    Example:
        old_win_path("C:/XAU_ELITE_AI/data/trade_memory.csv")
        → Path("/opt/leon/app/data/trade_memory.csv")
    """
    rel = win_path.replace("C:/XAU_ELITE_AI/", "")
    return BASE_DIR / rel
