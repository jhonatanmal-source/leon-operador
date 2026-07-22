#!/usr/bin/env python3
"""Validate each skill has required sections."""
import sys
from pathlib import Path

CODEX = Path(__file__).resolve().parent.parent
REQUIRED_SECTIONS = [
    "name", "description", "Objetivo", "Identificador",
    "Quando acionar", "Responsabilidades", "Regras"
]
errors = []

for skill_dir in sorted((CODEX / "skills").iterdir()):
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        errors.append(f"Missing SKILL.md in {skill_dir.name}")
        continue
    content = skill_file.read_text()
    for section in REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"Missing section '{section}' in {skill_dir.name}")

if errors:
    for e in errors:
        print(f"FAIL: {e}")
    sys.exit(1)
else:
    print("PASS: All skills validated")
    sys.exit(0)
