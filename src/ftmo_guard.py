# ===================================
# FTMO GUARD
# ===================================
#
# Camada de conformidade FTMO — guard ADICIONAL, nao substitui os guards
# existentes (risk_control_agent, smc_entry_guard, news_shield, autonomy).
#
# Principios:
#   1. DETECCAO AUTOMATICA da conta ao conectar — le login/server/trade_mode/
#      balance/equity de mt5.account_info(). NAO exige tamanho fixo de conta.
#   2. Limites FTMO sao PERCENTUAIS (5% dia / 10% drawdown total) — funcionam
#      para qualquer tamanho (10k/25k/100k) sem config manual.
#   3. Baseline por login: no primeiro connect de cada conta, grava o balance
#      inicial como ancora estavel de drawdown (equity oscila, balance nao).
#   4. Kill switch automatico com BUFFER interno (mais conservador que a FTMO):
#      pausa o dia em daily_buffer_percent; pausa geral em drawdown_buffer_percent.
#   5. Conta REAL/FUNDED continua BLOQUEADA por outros guards — este modulo
#      apenas CLASSIFICA (nao libera nada). trade_mode != DEMO e sinalizado.
#
# Nenhuma funcao aqui envia ordem. Somente leitura + calculo + estado local.

import configparser
import json
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from src.daily_entry_guard import evaluate_daily_entry_guard


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "config.ini"
DATA_DIR = ROOT_DIR / "data"
FTMO_ACCOUNTS_FILE = DATA_DIR / "ftmo_accounts.json"


# ── Configuracao ─────────────────────────────────────────────────────────

def _ftmo_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    defaults = {
        "enabled": True,
        # Regras oficiais FTMO (percentuais, independem do tamanho)
        "daily_loss_percent": 5.0,
        "max_drawdown_percent": 10.0,
        # Buffers internos — kill switch dispara ANTES do limite FTMO
        "daily_buffer_percent": 2.0,
        "drawdown_buffer_percent": 6.0,
        "min_trading_days": 4,
        "profit_target_percent": 8.0,
    }

    if not config.has_section("FTMO"):
        return defaults

    section = config["FTMO"]
    return {
        "enabled": section.get("enabled", "true").lower() == "true",
        "daily_loss_percent": section.getfloat(
            "daily_loss_percent", fallback=defaults["daily_loss_percent"]
        ),
        "max_drawdown_percent": section.getfloat(
            "max_drawdown_percent", fallback=defaults["max_drawdown_percent"]
        ),
        "daily_buffer_percent": section.getfloat(
            "daily_buffer_percent", fallback=defaults["daily_buffer_percent"]
        ),
        "drawdown_buffer_percent": section.getfloat(
            "drawdown_buffer_percent", fallback=defaults["drawdown_buffer_percent"]
        ),
        "min_trading_days": section.getint(
            "min_trading_days", fallback=defaults["min_trading_days"]
        ),
        "profit_target_percent": section.getfloat(
            "profit_target_percent", fallback=defaults["profit_target_percent"]
        ),
    }


# ── Estado de contas (baseline por login) ─────────────────────────────────

def _ler_contas():
    if not FTMO_ACCOUNTS_FILE.exists():
        return {}
    try:
        data = json.loads(FTMO_ACCOUNTS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _salvar_contas(contas):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FTMO_ACCOUNTS_FILE.write_text(
        json.dumps(contas, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def registrar_perfil_conta(login, server, currency, balance, trade_mode_demo):
    """Detecta/atualiza o perfil de uma conta ao conectar.

    No PRIMEIRO connect de um login, grava baseline_balance = balance atual
    (ancora de drawdown). Connects seguintes preservam o baseline original.
    Retorna o perfil (novo ou existente).
    """
    if login is None:
        return None
    if not isinstance(balance, (int, float)) or not math.isfinite(balance):
        return None

    key = str(login)
    contas = _ler_contas()
    perfil = contas.get(key)

    agora = datetime.now().isoformat(timespec="seconds")

    if perfil is None:
        # Primeira vez que vemos esta conta -> baseline = balance atual
        perfil = {
            "login": key,
            "server": server or "",
            "currency": currency or "",
            "baseline_balance": round(float(balance), 2),
            "is_demo": bool(trade_mode_demo),
            "first_seen": agora,
            "last_seen": agora,
        }
        contas[key] = perfil
        _salvar_contas(contas)
    else:
        # Conta ja conhecida -> preserva baseline, atualiza metadados
        perfil["last_seen"] = agora
        perfil["server"] = server or perfil.get("server", "")
        perfil["currency"] = currency or perfil.get("currency", "")
        perfil["is_demo"] = bool(trade_mode_demo)
        contas[key] = perfil
        _salvar_contas(contas)

    return perfil


# ── Calculo puro (testavel sem MT5) ────────────────────────────────────────

def avaliar_conformidade_ftmo(
    baseline_balance,
    equity_atual,
    resultado_dia,
    config=None,
):
    """Kill switch FTMO puro (sem MT5).

    Args:
        baseline_balance: balance inicial ancorado (baseline de drawdown)
        equity_atual: equity corrente (balance + P/L aberto)
        resultado_dia: P/L realizado + aberto do dia corrente (negativo = perda)
        config: dict de _ftmo_config() (opcional)

    Returns dict com approved (True = pode operar) + razoes.
    """
    if config is None:
        config = _ftmo_config()

    if not isinstance(baseline_balance, (int, float)) or not math.isfinite(
        baseline_balance
    ) or baseline_balance <= 0:
        return {
            "ok": False,
            "approved": False,
            "error": "INVALID_BASELINE_BALANCE",
        }
    if not isinstance(equity_atual, (int, float)) or not math.isfinite(equity_atual):
        return {"ok": False, "approved": False, "error": "INVALID_EQUITY"}
    if not isinstance(resultado_dia, (int, float)) or not math.isfinite(
        resultado_dia
    ):
        return {"ok": False, "approved": False, "error": "INVALID_DAILY_RESULT"}

    # Drawdown total vs baseline (percentual, independe do tamanho)
    drawdown_valor = baseline_balance - equity_atual
    drawdown_percent = (drawdown_valor / baseline_balance) * 100
    if drawdown_percent < 0:
        drawdown_percent = 0.0  # em lucro -> sem drawdown

    # Perda do dia (so conta se for perda; lucro nao bloqueia)
    perda_dia = abs(min(resultado_dia, 0.0))
    perda_dia_percent = (perda_dia / baseline_balance) * 100

    daily_buffer = config["daily_buffer_percent"]
    dd_buffer = config["drawdown_buffer_percent"]
    daily_ftmo = config["daily_loss_percent"]
    dd_ftmo = config["max_drawdown_percent"]

    razoes = []
    approved = True

    # Kill switch drawdown (buffer interno < limite FTMO)
    if drawdown_percent >= dd_buffer:
        approved = False
        razoes.append("DRAWDOWN_BUFFER_REACHED")

    # Kill switch perda diaria (buffer interno)
    if perda_dia_percent >= daily_buffer:
        approved = False
        razoes.append("DAILY_LOSS_BUFFER_REACHED")

    # Sinais de violacao REAL da FTMO (grave — nao deveria chegar aqui)
    ftmo_daily_violado = perda_dia_percent >= daily_ftmo
    ftmo_dd_violado = drawdown_percent >= dd_ftmo
    if ftmo_daily_violado:
        razoes.append("FTMO_DAILY_LIMIT_VIOLATED")
    if ftmo_dd_violado:
        razoes.append("FTMO_MAX_DRAWDOWN_VIOLATED")

    return {
        "ok": True,
        "approved": approved,
        "baseline_balance": round(float(baseline_balance), 2),
        "equity": round(float(equity_atual), 2),
        "drawdown_percent": round(drawdown_percent, 4),
        "daily_loss_percent": round(perda_dia_percent, 4),
        "daily_buffer_percent": daily_buffer,
        "drawdown_buffer_percent": dd_buffer,
        "ftmo_daily_limit_percent": daily_ftmo,
        "ftmo_max_drawdown_percent": dd_ftmo,
        "ftmo_daily_violated": ftmo_daily_violado,
        "ftmo_drawdown_violated": ftmo_dd_violado,
        "reasons": razoes,
        "reason": (
            "FTMO_GUARD_OK" if approved else ";".join(razoes)
        ),
    }


# ── Avaliacao com MT5 (leitura real) ───────────────────────────────────────

def avaliar_guard_ftmo():
    """Avalia o guard FTMO usando dados reais do MT5 (somente leitura).

    Detecta a conta automaticamente, registra/le o baseline por login,
    calcula perda diaria (deals do dia) e drawdown total, aplica o kill switch.
    """
    config = _ftmo_config()

    if not config["enabled"]:
        return {"ok": True, "approved": True, "reason": "FTMO_GUARD_DISABLED"}

    try:
        import mt5_safe as mt5
    except ImportError:
        return {"ok": False, "approved": False, "error": "MT5_IMPORT_ERROR"}

    if not mt5.initialize():
        return {
            "ok": False,
            "approved": False,
            "error": "MT5_INITIALIZE_FAILED",
            "details": str(mt5.last_error()),
        }

    try:
        account = mt5.account_info()
        if account is None:
            return {
                "ok": False,
                "approved": False,
                "error": "MT5_ACCOUNT_NOT_AVAILABLE",
            }

        is_demo = account.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO

        perfil = registrar_perfil_conta(
            login=account.login,
            server=account.server,
            currency=account.currency,
            balance=float(account.balance),
            trade_mode_demo=is_demo,
        )
        if perfil is None:
            return {
                "ok": False,
                "approved": False,
                "error": "FTMO_PROFILE_UNAVAILABLE",
            }

        baseline_balance = float(perfil["baseline_balance"])
        equity_atual = float(account.equity)

        # Resultado do dia: realizados (deals de saida) + aberto (account.profit)
        now = datetime.now(ZoneInfo("Europe/Prague"))
        start = now.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        deals = mt5.history_deals_get(int(start.timestamp()), int(now.timestamp()))
        if deals is None:
            return {"ok": False, "approved": False, "error": "DAILY_HISTORY_UNAVAILABLE"}
        exits = [
            deal
            for deal in deals
            if deal.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]
        ]
        realizado_dia = sum(
            float(deal.profit)
            + float(deal.commission)
            + float(deal.swap)
            + float(deal.fee)
            for deal in exits
        )
        resultado_dia = realizado_dia + float(account.profit)
        positions = mt5.positions_get()
        if positions is None:
            return {"ok": False, "approved": False, "error": "OPEN_POSITIONS_UNAVAILABLE"}
        open_ids = {int(getattr(p, "identifier", p.ticket)) for p in positions}
        closed_ids = {int(d.position_id) for d in deals
                      if d.entry in [mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY]
                      and int(d.position_id) not in open_ids}
        closed_results = []
        for position_id in closed_ids:
            history = mt5.history_deals_get(position=position_id)
            if history is None:
                return {"ok": False, "approved": False, "error": "CLOSED_HISTORY_UNAVAILABLE"}
            trades = [d for d in history if d.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]]
            if trades:
                net = sum(float(d.profit) + float(d.commission) + float(d.swap) + float(d.fee) for d in trades)
                closed_results.append((max(d.time for d in trades), net))
        closed_pnl = closed_peak = 0.0
        for _, net in sorted(closed_results):
            closed_pnl += net
            closed_peak = max(closed_peak, closed_pnl)

        resultado = avaliar_conformidade_ftmo(
            baseline_balance=baseline_balance,
            equity_atual=equity_atual,
            resultado_dia=resultado_dia,
            config=config,
        )
        resultado["login"] = str(account.login)
        resultado["is_demo"] = is_demo
        resultado["currency"] = account.currency
        try:
            daily = evaluate_daily_entry_guard(
                f"{account.server}:{account.login}", now.date().isoformat(),
                resultado_dia, baseline_balance, config["daily_buffer_percent"],
                closed_pnl=closed_pnl, closed_peak=closed_peak,
                giveback_balance=float(account.balance) - realizado_dia,
            )
        except (OSError, ValueError, TypeError, KeyError):
            return {"ok": False, "approved": False, "error": "DAILY_STATE_UNAVAILABLE"}
        resultado["daily_entry_guard"] = daily
        if not daily["approved"]:
            resultado["approved"] = False
            resultado["reasons"].append(daily["reason"])
            resultado["reason"] = ";".join(resultado["reasons"])
        return resultado
    finally:
        mt5.shutdown()


def resumo_ftmo():
    """Snapshot leve para painel/telegram (nao dispara ordem)."""
    config = _ftmo_config()
    return {
        "enabled": config["enabled"],
        "daily_loss_percent": config["daily_loss_percent"],
        "max_drawdown_percent": config["max_drawdown_percent"],
        "daily_buffer_percent": config["daily_buffer_percent"],
        "drawdown_buffer_percent": config["drawdown_buffer_percent"],
        "min_trading_days": config["min_trading_days"],
        "profit_target_percent": config["profit_target_percent"],
        "accounts": _ler_contas(),
    }
