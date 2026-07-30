import os
import json
from datetime import datetime
from pathlib import Path

VAULT = Path("/opt/leon/app/obsidian_vault")
DIARIO_DIR = VAULT / "aprendizados_diarios"
OPERACIONAL_DIR = VAULT / "operacional"
CONTEXTO_FILE = DIARIO_DIR / "CONTEXTO_EVOLUCAO.md"
INDICE_FILE = DIARIO_DIR / "INDICE.md"
STATS_FILE = VAULT / ".trade_stats.json"


def _ensure_dirs():
    DIARIO_DIR.mkdir(parents=True, exist_ok=True)
    OPERACIONAL_DIR.mkdir(parents=True, exist_ok=True)


def _load_stats():
    _ensure_dirs()
    if STATS_FILE.exists():
        try:
            return json.loads(STATS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"total": 0, "wins": 0, "losses": 0, "winrate": 0.0, "patterns": {}}


def _save_stats(stats):
    STATS_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False))


def save_trade_note(operation):
    pre_op_id = str(operation.get("id") or "SEM_ID")
    ativo = operation.get("ativo", "SEM_ATIVO")
    direcao = operation.get("direcao", "SEM_DIRECAO")
    result = operation.get("resultado", "SEM_RESULTADO")
    data = str(operation.get("data_fechamento") or datetime.now().isoformat())[:10]

    # Build markdown note
    outcome_text = "VENCEDORA" if str(result).startswith("WIN") else "PERDEDORA" if result == "LOSS" else result

    lines = [
        f"# {pre_op_id} — {ativo} {direcao} — {outcome_text}",
        "",
        f"**Data fechamento:** {data}",
        f"**Resultado:** {result}",
        "",
        "## Plano",
        f"- Entrada: {operation.get('entrada', '?')}",
        f"- Stop: {operation.get('stop', '?')}",
        f"- TP1: {operation.get('tp1', '?')}",
        f"- TP2: {operation.get('tp2', '?')}",
        f"- RR: 1:{operation.get('rr', '?')}",
        f"- Fechamento real: {operation.get('actual_close_price', '?')}",
        f"- Lucro/prejuizo: {operation.get('actual_profit', '?')}",
        f"- Motivo MT5: {operation.get('close_reason', '?')}",
        "",
        "## Contexto",
        f"- Setup: {operation.get('status_setup', '?')}",
        f"- SMC: {operation.get('smc', '?')}",
        f"- Elliott: {operation.get('elliott', '?')}",
        f"- BOS: {operation.get('bos', '?')}",
        f"- CHOCH: {operation.get('choch', '?')}",
        f"- FVG: {operation.get('fvg', '?')}",
        f"- Confianca: {operation.get('confianca', '?')}",
        f"- Brain Score: {operation.get('brain_score', '?')}",
        f"- Sessao: {operation.get('sessao', '?')}",
        f"- Context Mode: {operation.get('context_mode', '?')}",
        "",
        "## Observacao",
        f"{operation.get('observacao', '')}",
        "",
        "## Licao",
        _learning_text(operation),
        "",
    ]

    note = "\n".join(lines)
    filename = f"{pre_op_id}_{data}.md"
    filepath = OPERACIONAL_DIR / filename
    filepath.write_text(note)

    # Update stats
    stats = _load_stats()
    stats["total"] += 1
    if str(result).startswith("WIN"):
        stats["wins"] += 1
    elif result == "LOSS":
        stats["losses"] += 1
    if stats["total"] > 0:
        stats["winrate"] = round(stats["wins"] / stats["total"] * 100, 1)
    _save_stats(stats)

    return filepath


def _learning_text(operation):
    result = operation.get("resultado")
    if result == "LOSS":
        return (
            "Revisar se a zona, o gatilho M5 e o contexto top-down "
            "continuavam validos no momento da entrada. Verificar se "
            "houve sweep de liquidity na direcao oposta."
        )
    if result == "WIN_TP1":
        return (
            "A leitura entregou o primeiro alvo. Avaliar se travar "
            "parcial ou proteger breakeven seria viavel."
        )
    if result == "WIN_TP2":
        return (
            "A leitura alcancou o alvo tecnico principal. Registrar "
            "quais confluencias sustentaram o movimento para reuso."
        )
    return "Registrar o contexto e comparar com operacoes semelhantes."


def update_daily_learning(trade_note_path):
    hoje = datetime.now().strftime("%Y-%m-%d")
    filepath = DIARIO_DIR / f"{hoje}.md"

    if not filepath.exists():
        header = f"# Aprendizados Diarios — {hoje}\n\n"
        filepath.write_text(header)

    note_title = trade_note_path.stem
    with filepath.open("a") as f:
        f.write(f"- [[{note_title}]] — fechada em {hoje}\n")


def update_contexto_evolucao(operation):
    result = operation.get("resultado")
    smc = operation.get("smc", "?")
    elliott = operation.get("elliott", "?")
    direcao = operation.get("direcao", "?")
    brain = operation.get("brain_score", "?")

    if result == "LOSS":
        entry = (
            f"- {datetime.now().strftime('%Y-%m-%d')} | {operation.get('id')} "
            f"| LOSS {direcao} {operation.get('ativo')} "
            f"| SMC={smc} Elliott={elliott} Brain={brain} "
            f"| Revisar confirmacao antes da entrada"
        )
    elif str(result).startswith("WIN"):
        entry = (
            f"- {datetime.now().strftime('%Y-%m-%d')} | {operation.get('id')} "
            f"| {result} {direcao} {operation.get('ativo')} "
            f"| SMC={smc} Elliott={elliott} Brain={brain} "
            f"| Confluencia valida, registrar padrao"
        )
    else:
        return

    if not CONTEXTO_FILE.exists():
        base = CONTEXTO_FILE.read_text() if CONTEXTO_FILE.exists() else "# Contexto de Evolucao\n\n"
        CONTEXTO_FILE.write_text(base)

    with CONTEXTO_FILE.open("a") as f:
        f.write(entry + "\n")


def sync_closed_trade(operation):
    _ensure_dirs()
    path = save_trade_note(operation)
    update_daily_learning(path)
    update_contexto_evolucao(operation)
    return path
