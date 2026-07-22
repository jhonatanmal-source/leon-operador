#!/usr/bin/env python3
"""Validate command files exist and have frontmatter."""
import sys
from pathlib import Path

CODEX = Path(__file__).resolve().parent.parent
REQUIRED_COMMANDS = [
    "leon-missao", "leon-corrigir", "leon-auditar", "leon-testar",
    "leon-revisar", "leon-refatorar", "leon-otimizar", "leon-vps",
    "leon-seguranca", "leon-observabilidade", "leon-release",
    "leon-status", "leon-retomar", "leon-relatorio"
]
errors = []

for cmd in REQUIRED_COMMANDS:
    cmd_file = CODEX / "commands" / f"{cmd}.md"
    if not cmd_file.exists():
        errors.append(f"Missing command: {cmd}.md")
        continue
    content = cmd_file.read_text()
    if not content.startswith("---"):
        errors.append(f"Command {cmd} missing frontmatter")

if errors:
    for e in errors:
        print(f"FAIL: {e}")
    sys.exit(1)
else:
    print("PASS: All commands validated")
    sys.exit(0)
