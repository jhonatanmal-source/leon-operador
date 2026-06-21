import json
from pathlib import Path

from telegram_engine import enviar_mensagem


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
STATE_FILE = DATA_DIR / "operation_close_alerts.json"


def _load_sent():
    if not STATE_FILE.exists():
        return set()

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()

    return set(data if isinstance(data, list) else [])


def _save_sent(sent):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(sorted(sent), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _outcome_text(result):
    if str(result).startswith("WIN"):
        return "VENCEDORA"
    if result == "LOSS":
        return "PERDEDORA"
    return str(result or "SEM RESULTADO")


def _learning_text(operation):
    result = operation.get("resultado")
    if result == "LOSS":
        return (
            "Revisar se a zona, o gatilho M5 e o contexto top-down "
            "continuavam validos no momento da entrada."
        )
    if result == "WIN_TP1":
        return (
            "A leitura entregou o primeiro alvo. Revisar se a protecao parcial "
            "seria melhor que manter toda a posicao."
        )
    if result == "WIN_TP2":
        return (
            "A leitura alcançou o alvo tecnico principal. Registrar quais "
            "confluencias sustentaram o movimento."
        )
    return "Registrar o contexto e comparar com operacoes semelhantes."


def build_close_message(operation):
    candle = operation.get("candle") or {}
    result = operation.get("resultado")
    actual_close = operation.get("actual_close_price")
    actual_profit = operation.get("actual_profit")
    close_reason = operation.get("close_reason")

    lines = [
        "LEON | OPERACAO FINALIZADA",
        "",
        f"Resultado: {_outcome_text(result)}",
        f"Fechamento: {result}",
        f"Ativo: {operation.get('ativo', 'SEM DADOS')}",
        f"Direcao: {operation.get('direcao', 'SEM DADOS')}",
        (
            f"Lucro/prejuizo real: {actual_profit}"
            if actual_profit is not None
            else None
        ),
        (
            f"Motivo MT5: {close_reason}"
            if close_reason
            else None
        ),
        "",
        "[ PLANO ]",
        f"- Entrada: {operation.get('entrada', 'SEM DADOS')}",
        f"- Stop: {operation.get('stop', 'SEM DADOS')}",
        f"- TP1: {operation.get('tp1', 'SEM DADOS')}",
        f"- TP2: {operation.get('tp2', 'SEM DADOS')}",
        f"- RR tecnico: 1:{operation.get('rr', 'SEM DADOS')}",
        (
            f"- Fechamento real: {actual_close}"
            if actual_close is not None
            else None
        ),
        "",
        "[ CONTEXTO ]",
        f"- Setup: {operation.get('status_setup', 'SEM DADOS')}",
        f"- SMC: {operation.get('smc', 'SEM DADOS')}",
        f"- Elliott: {operation.get('elliott', 'SEM DADOS')}",
        f"- BOS: {operation.get('bos', 'SEM DADOS')}",
        f"- CHOCH: {operation.get('choch', 'SEM DADOS')}",
        f"- Confianca: {operation.get('confianca', 'SEM DADOS')}",
        f"- Brain Score: {operation.get('brain_score', 'SEM DADOS')}",
    ]

    if candle:
        lines.extend([
            "",
            "[ CANDLE DE FECHAMENTO ]",
            f"- Horario: {candle.get('data', operation.get('data_fechamento', 'SEM DADOS'))}",
            f"- Maxima: {candle.get('high', 'SEM DADOS')}",
            f"- Minima: {candle.get('low', 'SEM DADOS')}",
            f"- Fechamento: {candle.get('close', 'SEM DADOS')}",
        ])

    lines.extend([
        "",
        "[ APRENDIZADO ]",
        f"- {_learning_text(operation)}",
    ])

    return "\n".join(str(line) for line in lines if line is not None)


def send_operation_close_alert(operation):
    operation_id = str(operation.get("id") or "").strip()
    result = str(operation.get("resultado") or "").strip()
    key = f"{operation_id}:{result}"

    if not operation_id or not result:
        return {"ok": False, "error": "INVALID_OPERATION_CLOSE_ALERT"}

    sent = _load_sent()
    if key in sent:
        return {
            "ok": True,
            "skipped": True,
            "reason": "OPERATION_CLOSE_ALERT_ALREADY_SENT",
            "key": key,
        }

    response = enviar_mensagem(build_close_message(operation))
    if response.get("ok"):
        sent.add(key)
        _save_sent(sent)

    return response
