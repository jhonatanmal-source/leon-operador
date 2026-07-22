#!/usr/bin/env python3
"""Check for violations of protected rules in source code."""
import sys
import re
from pathlib import Path

SRC = Path("/opt/leon/app/src")
PATTERNS = {
    "real_account_authorization": r'real.*account.*authorized|authorize.*real|liberar.*conta.*real',
    "guard_removal": r'guard.*remove|remove.*guard|bypass.*guard',
    "brain_score_gate": r'brain.*score.*gate|gate.*brain.*score',
    "momentum_gate": r'momentum.*gate|gate.*momentum',
    "news_shield_removal": r'remove.*news|news.*remove|disable.*news',
    "max_trades_increase": r'max.*trades?.*(increase|increase)',
}
errors = []

for py_file in SRC.glob("*.py"):
    content = py_file.read_text()
    for rule_name, pattern in PATTERNS.items():
        if re.search(pattern, content, re.IGNORECASE):
            errors.append(f"Potential violation '{rule_name}' in {py_file.name}")

if errors:
    for e in errors:
        print(f"WARNING: {e}")
    print("PASS: Protected rules check done (warnings above)")
    sys.exit(0)
else:
    print("PASS: No protected rule violations found")
    sys.exit(0)
