#!/usr/bin/env python3
"""Validate that report files have required structure."""
import sys
from pathlib import Path

TAREFAS = Path("/opt/leon/app/tarefas")
REQUIRED_SECTIONS = [
    "STATUS", "RESUMO EXECUTIVO", "AMBIENTE",
    "ARQUIVOS CRIADOS", "TESTES EXECUTADOS",
    "RISCOS", "PRÓXIMOS PASSOS"
]

report_files = list(TAREFAS.glob("relatorio_final_*.md"))
if not report_files:
    print("WARNING: No final report found")
    sys.exit(0)

errors = []
for report in report_files:
    content = report.read_text()
    for section in REQUIRED_SECTIONS:
        if section not in content.upper() and section not in content:
            errors.append(f"Missing section '{section}' in {report.name}")

if errors:
    for e in errors:
        print(f"FAIL: {e}")
    sys.exit(1)
else:
    print(f"PASS: {len(report_files)} reports validated")
    sys.exit(0)
