# ===================================
# RISK CONTROL AGENT
# ===================================

import configparser
from datetime import datetime
from pathlib import Path

from risk_method_engine import obter_metodo


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "config.ini"
CONTRACT_SIZE_XAU = 100


def _risk_config():

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if not config.has_section("RISK_CONTROL"):
        return {
            "enabled": True,
            "risk_percent": 0.5,
            "max_risk_percent": 1.0,
            "daily_loss_percent": 2.0,
            "max_lot": 0.01,
            "min_lot": 0.01,
            "correction_risk_factor": 0.5,
            "max_open_risk_percent": 1.0,
        }

    section = config["RISK_CONTROL"]

    return {
        "enabled": section.get("enabled", "true").lower() == "true",
        "risk_percent": section.getfloat("risk_percent", fallback=0.5),
        "max_risk_percent": section.getfloat("max_risk_percent", fallback=1.0),
        "daily_loss_percent": section.getfloat("daily_loss_percent", fallback=2.0),
        "max_lot": section.getfloat("max_lot", fallback=0.01),
        "min_lot": section.getfloat("min_lot", fallback=0.01),
        "correction_risk_factor": section.getfloat(
            "correction_risk_factor",
            fallback=0.5,
        ),
        "max_open_risk_percent": section.getfloat(
            "max_open_risk_percent",
            fallback=1.0,
        ),
    }


def _obter_saldo_mt5():

    try:
        import MetaTrader5 as mt5

        if not mt5.initialize():
            return None

        account = mt5.account_info()
        mt5.shutdown()

        if account is None:
            return None

        return float(account.balance)

    except Exception:
        return None


def calcular_limite_perda_diaria(
    saldo_atual,
    resultado_realizado,
    resultado_aberto,
    limite_percentual,
):
    saldo_inicio = saldo_atual - resultado_realizado
    if saldo_inicio <= 0:
        return {
            "ok": False,
            "approved": False,
            "error": "INVALID_STARTING_BALANCE",
        }

    resultado_total = resultado_realizado + resultado_aberto
    limite_valor = saldo_inicio * (limite_percentual / 100)
    perda_percentual = (
        abs(min(resultado_total, 0)) / saldo_inicio
    ) * 100
    aprovado = resultado_total > -limite_valor

    return {
        "ok": True,
        "approved": aprovado,
        "starting_balance": round(saldo_inicio, 2),
        "current_balance": round(saldo_atual, 2),
        "realized_result": round(resultado_realizado, 2),
        "open_result": round(resultado_aberto, 2),
        "total_result": round(resultado_total, 2),
        "daily_loss_limit_percent": round(limite_percentual, 3),
        "daily_loss_limit_value": round(limite_valor, 2),
        "current_loss_percent": round(perda_percentual, 4),
        "reason": (
            "DAILY_LOSS_LIMIT_OK"
            if aprovado
            else "DAILY_LOSS_LIMIT_REACHED"
        ),
    }


def avaliar_limite_perda_diaria():
    config = _risk_config()

    try:
        import MetaTrader5 as mt5
    except ImportError:
        return {
            "ok": False,
            "approved": False,
            "error": "MT5_IMPORT_ERROR",
        }

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

        start = datetime.now().replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        deals = mt5.history_deals_get(start, datetime.now()) or []
        exits = [
            deal
            for deal in deals
            if deal.entry in [mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY]
        ]
        resultado_realizado = sum(
            float(deal.profit)
            + float(deal.commission)
            + float(deal.swap)
            + float(deal.fee)
            for deal in exits
        )
        resultado_aberto = float(account.profit)

        return calcular_limite_perda_diaria(
            saldo_atual=float(account.balance),
            resultado_realizado=resultado_realizado,
            resultado_aberto=resultado_aberto,
            limite_percentual=config["daily_loss_percent"],
        )
    finally:
        mt5.shutdown()


def calcular_plano_risco(pre_operacao, saldo=None):

    config = _risk_config()
    metodo = obter_metodo(pre_operacao.get("metodo_risco") or None)

    if saldo is None:
        saldo = _obter_saldo_mt5()

    if saldo is None:
        saldo = 1000.0

    try:
        entrada = float(pre_operacao["entrada"])
        stop = float(pre_operacao["stop"])
    except (KeyError, TypeError, ValueError):
        return {
            "ok": False,
            "error": "INVALID_PRE_OPERATION_PRICE",
            "enabled": config["enabled"],
        }

    distancia_stop = abs(entrada - stop)

    if distancia_stop <= 0:
        return {
            "ok": False,
            "error": "INVALID_STOP_DISTANCE",
            "enabled": config["enabled"],
        }

    risco_percentual = min(
        metodo["risk_percent"],
        config["max_risk_percent"],
    )
    context_mode = pre_operacao.get("context_mode") or "TENDENCIA"
    if context_mode == "CORRECAO":
        risco_percentual *= config["correction_risk_factor"]
    risco_valor = saldo * (risco_percentual / 100)
    lote_calculado = risco_valor / (distancia_stop * CONTRACT_SIZE_XAU)
    lote = round(lote_calculado, 2)
    lote_original = lote

    if lote < config["min_lot"]:
        lote = config["min_lot"]

    if lote > config["max_lot"]:
        lote = config["max_lot"]

    risco_estimado = round(distancia_stop * CONTRACT_SIZE_XAU * lote, 2)
    risco_estimado_percent = round((risco_estimado / saldo) * 100, 3)
    lote_capado = lote != lote_original
    risco_acima_do_alvo = risco_estimado_percent > risco_percentual

    aprovado = (
        config["enabled"]
        and risco_estimado_percent <= config["max_risk_percent"]
        and lote <= config["max_lot"]
    )

    return {
        "ok": True,
        "enabled": config["enabled"],
        "approved": aprovado,
        "saldo": round(saldo, 2),
        "risk_percent": risco_percentual,
        "method": metodo["name"],
        "context_mode": context_mode,
        "rr_target": metodo["rr_target"],
        "risk_value": round(risco_valor, 2),
        "stop_distance": round(distancia_stop, 2),
        "calculated_lot": round(lote_calculado, 4),
        "lot": lote,
        "lot_capped": lote_capado,
        "max_lot": config["max_lot"],
        "estimated_risk": risco_estimado,
        "estimated_risk_percent": risco_estimado_percent,
        "risk_above_target": risco_acima_do_alvo,
        "daily_loss_percent": config["daily_loss_percent"],
        "reason": (
            "Risco aprovado pelo agente gestor."
            if aprovado
            else "Risco bloqueado pelo agente gestor."
        ),
    }


def avaliar_orcamento_risco_aberto(risco_planejado_percentual):
    config = _risk_config()

    try:
        import MetaTrader5 as mt5
    except ImportError:
        return {
            "ok": False,
            "approved": False,
            "error": "MT5_IMPORT_ERROR",
        }

    if not mt5.initialize():
        return {
            "ok": False,
            "approved": False,
            "error": "MT5_INITIALIZE_FAILED",
        }

    try:
        account = mt5.account_info()
        positions = mt5.positions_get() or []
        if account is None or account.balance <= 0:
            return {
                "ok": False,
                "approved": False,
                "error": "MT5_ACCOUNT_NOT_AVAILABLE",
            }

        risco_aberto = 0.0
        sem_stop = []
        for position in positions:
            stop = float(getattr(position, "sl", 0) or 0)
            if stop <= 0:
                sem_stop.append(getattr(position, "ticket", None))
                continue

            symbol = mt5.symbol_info(position.symbol)
            contract_size = float(
                getattr(symbol, "trade_contract_size", CONTRACT_SIZE_XAU)
                or CONTRACT_SIZE_XAU
            )
            risco_aberto += (
                abs(float(position.price_open) - stop)
                * float(position.volume)
                * contract_size
            )

        if sem_stop:
            return {
                "ok": True,
                "approved": False,
                "error": "OPEN_POSITION_WITHOUT_STOP",
                "tickets": sem_stop,
            }

        risco_aberto_percentual = risco_aberto / float(account.balance) * 100
        risco_total = risco_aberto_percentual + float(
            risco_planejado_percentual
        )
        limite = config["max_open_risk_percent"]

        return {
            "ok": True,
            "approved": risco_total <= limite,
            "open_risk_percent": round(risco_aberto_percentual, 4),
            "planned_risk_percent": round(
                float(risco_planejado_percentual),
                4,
            ),
            "total_risk_percent": round(risco_total, 4),
            "max_open_risk_percent": limite,
        }
    finally:
        mt5.shutdown()


def resumo_risco():

    config = _risk_config()
    saldo = _obter_saldo_mt5()
    metodo = obter_metodo()

    return {
        "enabled": config["enabled"],
        "balance": saldo,
        "risk_percent": config["risk_percent"],
        "method": metodo["name"],
        "method_risk_percent": metodo["risk_percent"],
        "method_rr_target": metodo["rr_target"],
        "method_daily_loss_percent": metodo["daily_loss_percent"],
        "max_risk_percent": config["max_risk_percent"],
        "daily_loss_percent": config["daily_loss_percent"],
        "min_lot": config["min_lot"],
        "max_lot": config["max_lot"],
    }
