# ===================================
# AUTOMATIC LEARNING CAPTURE
# ===================================
"""
Mechanism for automatic learning capture during the LEON XAU ELITE AI mission flow.
Integrates with mission phases and saves learnings to the daily diary system.

Phases captured:
  - TRIAGEM start
  - DIAGNÓSTICO complete
  - PLANO complete
  - IMPLEMENTATION complete
  - TESTES complete

Safety: Never exposes real account data, strategy details, TP, SL values.
Only captures structural patterns, errors, decisions, and infrastructure notes.
"""

import re
from datetime import date, datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DIARIOS_DIR = ROOT_DIR / "tarefas" / "aprendizados_diarios"
CONTEXTO_EVOLUCAO_FILE = DIARIOS_DIR / "CONTEXTO_EVOLUCAO.md"
INDICE_FILE = DIARIOS_DIR / "INDICE.md"

# Mission phase constants
PHASE_TRIAGEM = "TRIAGEM"
PHASE_DIAGNOSTICO = "DIAGNÓSTICO"
PHASE_PLANO = "PLANO"
PHASE_IMPLEMENTATION = "IMPLEMENTATION"
PHASE_TESTES = "TESTES"

# Sensitive keywords that must never be logged (never write these to files)
SENSITIVE_KEYWORDS = {
    "senha",
    "password",
    "token",
    "conta real",
    "account real",
    "trade_mode_real",
    "trade_mode_demo",
    "tp ",
    "sl ",
    "take profit",
    "stop loss",
    "entry_price",
    "stop_price",
    "tp1_price",
    "tp2_price",
    "gold_spot",
    "xauusd",
    "price ",
    "bid ",
    "ask ",
    "stop ",
    "risk ",
    "rr ",
    "reward",
    "risk:reward",
    "balance",
    "equity",
    "lot",
    "volume",
}


def _is_sensitive(text: str) -> bool:
    """Check if text contains sensitive information that should not be logged."""
    if not text:
        return False
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in SENSITIVE_KEYWORDS)


def _sanitize_text(text: str) -> str:
    """Remove or mask sensitive information from text before logging."""
    if not text:
        return text
    sanitized = text
    for keyword in SENSITIVE_KEYWORDS:
        # Case-insensitive replacement
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


def _today_filename() -> str:
    """Return today's date filename YYYY-MM-DD."""
    return date.today().strftime("%Y-%m-%d")


def _ensure_daily_file() -> Path:
    """Ensure the daily learning file exists with proper header."""
    filename = _today_filename()
    daily_file = DIARIOS_DIR / f"{filename}.md"
    DIARIOS_DIR.mkdir(parents=True, exist_ok=True)
    if not daily_file.exists():
        daily_file.write_text(
            f"# Aprendizados Diários — {filename}\n\n", encoding="utf-8"
        )
    return daily_file


def _append_learning_entry(learning_text: str) -> None:
    """
    Append a learning entry to today's daily file.

    Format: - [HH:MM:SS] | summary
    Appends to the end of the file, following the existing diary pattern.
    """
    daily_file = _ensure_daily_file()
    sanitized = _sanitize_text(learning_text)

    # Avoid duplicate entries (compare sanitized text)
    existing = daily_file.read_text(encoding="utf-8")
    if sanitized not in existing:
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"- [{timestamp}] | {sanitized}\n"
        daily_file.write_text(existing + entry, encoding="utf-8")


def _promote_to_contexto_evolucao(patterns: list[str]) -> None:
    """Promote recurring patterns to CONTEXTO_EVOLUCAO.md."""
    if not patterns:
        return

    CONTEXTO_EVOLUCAO_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Read existing contexto
    existente = ""
    if CONTEXTO_EVOLUCAO_FILE.exists():
        existente = CONTEXTO_EVOLUCAO_FILE.read_text(encoding="utf-8")

    # Check for manual curation marker
    is_manual_curated = "<!-- CURADO MANUALMENTE --" in existente or "CURADO_MANUALMENTE" in existente

    # If manually curated, skip automatic promotion to preserve human curation
    if is_manual_curated:
        return

    # Identify section presence
    has_padroes = "## Padrões Identificados" in existente
    has_decisoes = "## Decisões Estruturais" in existente

    # Build promoted content - add patterns to appropriate sections
    added_any = False
    new_lines = []

    for line in existente.splitlines():
        new_lines.append(line)
        # Add pattern to Padrões Identificados section
        if "## Padrões Identificados" in line and not added_any:
            for pattern in patterns:
                sanitized_pattern = _sanitize_text(pattern)
                # Skip if already present in this section
                section_text = "\n".join(new_lines)
                if f"- {sanitized_pattern}" not in section_text:
                    new_lines.append(f"- {sanitized_pattern}")
                    added_any = True
        # Add pattern to Decisões Estruturais section if no patterns section yet
        elif "## Decisões Estruturais" in line and not added_any:
            for pattern in patterns:
                sanitized_pattern = _sanitize_text(pattern)
                section_text = "\n".join(new_lines)
                if f"- {sanitized_pattern}" not in section_text:
                    new_lines.append(f"- {sanitized_pattern}")
                    added_any = True

    # If we added patterns, also add the section headers if they don't exist
    if added_any:
        final_text = "\n".join(new_lines)
        # Ensure Padrões Identificados section exists
        if "## Padrões Identificados" not in final_text and "## Decisões Estruturais" not in final_text:
            # Create minimal contexto structure
            minimal = (
                "# Contexto de Evolução — Aprendizados Acumulados\n\n"
                "Este arquivo é carregado por todos os agentes ao iniciar uma missão.\n"
                "Contém padrões, decisões, erros e correções acumulados que evoluem o conhecimento da equipe.\n\n"
                "## Como usar\n"
                "- Leia este arquivo no início de cada missão\n"
                "- Adicione novos aprendizados ao final do dia em `tarefas/aprendizados_diarios/YYYY-MM-DD.md`\n"
                "- Apenas padrões recorrentes e decisões estruturais devem ser promovidos para cá\n"
                "---\n\n"
                "## Padrões Identificados\n\n"
            )
            final_text = minimal + final_text
            # Re-add the patterns
            for pattern in patterns:
                sanitized_pattern = _sanitize_text(pattern)
                if f"- {sanitized_pattern}" not in final_text:
                    final_text += f"- {sanitized_pattern}\n"

        # Write updated contexto
        CONTEXTO_EVOLUCAO_FILE.write_text(final_text, encoding="utf-8")
        # Sync to vault
        VAULT_CONTEXTO = ROOT_DIR / "obsidian_vault" / "aprendizados_diarios" / "CONTEXTO_EVOLUCAO.md"
        if VAULT_CONTEXTO.exists() or added_any:
            VAULT_CONTEXTO.parent.mkdir(parents=True, exist_ok=True)
            VAULT_CONTEXTO.write_text(final_text, encoding="utf-8")


def _update_indice() -> None:
    """Update the INDICE.md with today's entry."""
    INDICE_FILE.parent.mkdir(parents=True, exist_ok=True)
    daily_file = DIARIOS_DIR / f"{_today_filename()}.md"
    primeira_linha = ""
    if daily_file.exists():
        linhas = daily_file.read_text(encoding="utf-8").splitlines()
        if linhas:
            primeira_linha = linhas[0].lstrip("# ").strip()

    if INDICE_FILE.exists():
        conteudo = INDICE_FILE.read_text(encoding="utf-8")
        # Check if today already in index
        if f"| {_today_filename()} |" not in conteudo:
            linhas_idx = conteudo.splitlines()
            added = False
            new_lines = []
            for line in linhas_idx:
                if line.startswith("| Data | Resumo |") or line.startswith("|------|--------|"):
                    new_lines.append(line)
                    continue
                if not added and line.strip() and not line.startswith("|"):
                    # After the header row, add our row
                    new_lines.append(f"| {_today_filename()} | {primeira_linha} |")
                    added = True
                new_lines.append(line)
            if not added:
                new_lines.append(f"| {_today_filename()} | {primeira_linha} |")
            INDICE_FILE.write_text("\n".join(new_lines), encoding="utf-8")


class LearningCapture:
    """
    Automatic learning capture for mission phases.
    Each method captures a learning at the specified phase and saves it
    to the appropriate daily file. After mission end, recurring patterns
    are promoted to CONTEXTO_EVOLUCAO.md.

    Safety: All captured text is sanitized to remove sensitive data
    (TP, SL, account numbers, passwords, tokens, etc.).
    """

    def __init__(self):
        self.today = _today_filename()
        self.mission_started = False
        self.captured_learnings = {
            PHASE_TRIAGEM: [],
            PHASE_DIAGNOSTICO: [],
            PHASE_PLANO: [],
            PHASE_IMPLEMENTATION: [],
            PHASE_TESTES: [],
        }
        self._phase_descriptions = {
            PHASE_TRIAGEM: "Missão iniciada",
            PHASE_DIAGNOSTICO: "Diagnóstico concluído",
            PHASE_PLANO: "Plano concluído",
            PHASE_IMPLEMENTATION: "Implementação concluída",
            PHASE_TESTES: "Testes concluídos",
        }

    def start_mission(self) -> None:
        """Call at TRIAGEM start - initializes the mission learning capture."""
        self.mission_started = True
        self.captured_learnings = {phase: [] for phase in self.captured_learnings}
        learning_text = self._phase_descriptions[PHASE_TRIAGEM]
        _append_learning_entry(learning_text)
        self.captured_learnings[PHASE_TRIAGEM].append(learning_text)

    def diagnostic_complete(self, summary: str = "") -> None:
        """Call at DIAGNÓSTICO complete - captures diagnostic learnings."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        summary_text = summary or self._phase_descriptions[PHASE_DIAGNOSTICO]
        learning_text = f"{self._phase_descriptions[PHASE_DIAGNOSTICO]}: {summary_text}"
        # Sanitize and append
        _append_learning_entry(learning_text)
        self.captured_learnings[PHASE_DIAGNOSTICO].append(learning_text)

    def plano_complete(self, summary: str = "") -> None:
        """Call at PLANO complete - captures planning learnings."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        summary_text = summary or self._phase_descriptions[PHASE_PLANO]
        learning_text = f"{self._phase_descriptions[PHASE_PLANO]}: {summary_text}"
        _append_learning_entry(learning_text)
        self.captured_learnings[PHASE_PLANO].append(learning_text)

    def implementation_complete(self, summary: str = "") -> None:
        """Call at IMPLEMENTATION complete - captures implementation learnings."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        summary_text = summary or self._phase_descriptions[PHASE_IMPLEMENTATION]
        learning_text = f"{self._phase_descriptions[PHASE_IMPLEMENTATION]}: {summary_text}"
        _append_learning_entry(learning_text)
        self.captured_learnings[PHASE_IMPLEMENTATION].append(learning_text)

    def testes_complete(self, summary: str = "") -> None:
        """Call at TESTES complete - captures test learnings."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        summary_text = summary or self._phase_descriptions[PHASE_TESTES]
        learning_text = f"{self._phase_descriptions[PHASE_TESTES]}: {summary_text}"
        _append_learning_entry(learning_text)
        self.captured_learnings[PHASE_TESTES].append(learning_text)

    def end_mission(self) -> None:
        """Call at end of mission - promotes recurring patterns to CONTEXTO_EVOLUCAO.md."""
        # Consolidate learnings and identify promotable patterns
        all_learnings = []
        for phase_learnings in self.captured_learnings.values():
            all_learnings.extend(phase_learnings)

        # Identify patterns worth promoting (filtering sensitive data)
        promotable = []
        for learning in all_learnings:
            text = _sanitize_text(learning)
            if not _is_sensitive(text):
                # Only promote structural patterns (errors, decisions, infrastructure)
                # Skip: strategy details, TP, SL, account data, pricing
                promotable.append(text)

        # Promote to CONTEXTO_EVOLUCAO.md (limit to 5 patterns per mission)
        _promote_to_contexto_evolucao(promotable[:5])

        # Update INDICE.md
        _update_indice()