#!/usr/bin/env python3
"""Validate .codex directory structure."""
import sys
from pathlib import Path

CODEX = Path(__file__).resolve().parent.parent
REQUIRED_DIRS = ["config", "skills", "commands", "memory", "templates", "validators"]
REQUIRED_CONFIGS = ["governance.md", "safety_rules.md", "coding_standards.md", "testing_policy.md", "reporting_policy.md", "permissions_matrix.md", "project_context.md"]
REQUIRED_SKILLS = 25
REQUIRED_COMMANDS = 14
REQUIRED_MEMORY = 6
REQUIRED_TEMPLATES = 8

errors = []

for d in REQUIRED_DIRS:
    if not (CODEX / d).exists():
        errors.append(f"Missing directory: .codex/{d}")

for cfg in REQUIRED_CONFIGS:
    if not (CODEX / "config" / cfg).exists():
        errors.append(f"Missing config: config/{cfg}")

skill_dirs = list((CODEX / "skills").iterdir())
if len(skill_dirs) < REQUIRED_SKILLS:
    errors.append(f"Expected {REQUIRED_SKILLS} skills, found {len(skill_dirs)}")

cmd_files = list((CODEX / "commands").glob("*.md"))
if len(cmd_files) < REQUIRED_COMMANDS:
    errors.append(f"Expected {REQUIRED_COMMANDS} commands, found {len(cmd_files)}")

mem_files = list((CODEX / "memory").glob("*.md"))
if len(mem_files) < REQUIRED_MEMORY:
    errors.append(f"Expected {REQUIRED_MEMORY} memory files, found {len(mem_files)}")

tpl_files = list((CODEX / "templates").glob("*"))
if len(tpl_files) < REQUIRED_TEMPLATES:
    errors.append(f"Expected {REQUIRED_TEMPLATES} templates, found {len(tpl_files)}")

if errors:
    for e in errors:
        print(f"FAIL: {e}")
    sys.exit(1)
else:
    print("PASS: Structure validation OK")
    sys.exit(0)
