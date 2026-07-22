# ===================================
# RISK CONTROL AGENT
# ===================================

import configparser
import math
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

from src.risk_method_engine import obter_metodo


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
        import mt5linux_compat as mt5

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
    if not math.isfinite(saldo_atual):
        return {
            "ok": False,
            "approved": False,
            "error": "INVALID_STARTING_BALANCE",
            "reason": "saldo_atual nao finito",
        }

    if not math.isfinite(resultado_realizado) or not math.isfinite(resultado_aberto):
        return {
            "ok": False,
            "approved": False,
            "error": "INVALID_RESULT",
            "reason": "resultado nao finito",
        }

    if limite_percentual <= 0:
        return {
            "ok": False,
            "approved": False,
            "error": "INVALID_LOSS_LIMIT",
            "reason": "limite_percentual deve ser positivo",
        }

    saldo_inicio = saldo_atual - resultado_realizado
    if saldo_inicio <= 0:
        return {
            "ok": False,
            "approved": False,
            "error": "INVALID_STARTING_BALANCE",
            "reason": "saldo_inicio nao positivo",
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
        import mt5linux_compat as mt5
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


def _validar_especificacoes(esp):
    if not isinstance(esp, dict):
        return {"ok": False, "error": "INVALID_SPECIFICATION"}
    erros = []
    for campo, nome in [
        ("contract_size", "INVALID_CONTRACT_SIZE"),
        ("volume_step", "INVALID_VOLUME_STEP"),
        ("volume_min", "INVALID_VOLUME_LIMITS"),
        ("volume_max", "INVALID_VOLUME_LIMITS"),
    ]:
        valor = esp.get(campo)
        if not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor <= 0:
            erros.append(nome)
    for campo, nome in [("tick_size", "INVALID_TICK_SPECIFICATION"), ("tick_value", "INVALID_TICK_SPECIFICATION")]:
        valor = esp.get(campo)
        if valor is not None and (not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor <= 0):
            erros.append(nome)
    if not erros and esp.get("volume_min", 0) > esp.get("volume_max", float("inf")):
        erros.append("INVALID_VOLUME_LIMITS")
    if erros:
        return {"ok": False, "error": erros[0]}
    return {"ok": True}


def _normalizar_lote(lote_bruto, volume_step):
    if not math.isfinite(lote_bruto) or lote_bruto < 0:
        return None
    if not math.isfinite(volume_step) or volume_step <= 0:
        return None

    lote_d = Decimal(str(lote_bruto))
    step_d = Decimal(str(volume_step))

    steps = (lote_d / step_d).to_integral_value(rounding=ROUND_FLOOR)
    lote_normalizado = steps * step_d

    lote_float = float(lote_normalizado)

    if not math.isfinite(lote_float):
        return None

    return lote_float


def calcular_plano_risco(pre_operacao, saldo=None, especificacoes=None):

    config = _risk_config()
    metodo = obter_metodo(pre_operacao.get("metodo_risco") or None)

    if saldo is None:
        saldo = _obter_saldo_mt5()

    if saldo is None:
        saldo = 1000.0

    if not math.isfinite(saldo):
        return {
            "ok": False,
            "error": "INVALID_BALANCE",
            "enabled": config["enabled"],
        }

    try:
        entrada = float(pre_operacao["entrada"])
        stop = float(pre_operacao["stop"])
    except (KeyError, TypeError, ValueError):
        return {
            "ok": False,
            "error": "INVALID_PRE_OPERATION_PRICE",
            "enabled": config["enabled"],
        }

    if not math.isfinite(entrada) or not math.isfinite(stop):
        return {
            "ok": False,
            "error": "INVALID_PRE_OPERATION_PRICE",
            "enabled": config["enabled"],
        }

    distancia_stop = abs(entrada - stop)

    if distancia_stop <= 0 or not math.isfinite(distancia_stop):
        return {
            "ok": False,
            "error": "INVALID_STOP_DISTANCE",
            "enabled": config["enabled"],
        }

    esp = dict(especificacoes or {})
    esp.setdefault("contract_size", CONTRACT_SIZE_XAU)
    esp.setdefault("volume_step", 0.01)
    esp.setdefault("volume_min", config["min_lot"])
    esp.setdefault("volume_max", config["max_lot"])
    validacao = _validar_especificacoes(esp)
    if not validacao["ok"]:
        return {
            "ok": False,
            "error": validacao["error"],
            "enabled": config["enabled"],
        }

    contract_size = esp["contract_size"]
    volume_step = esp["volume_step"]
    volume_min = min(esp["volume_min"], config["min_lot"])
    volume_max = min(esp["volume_max"], config["max_lot"])

    if saldo <= 0:
        return {
            "ok": False,
            "error": "INVALID_BALANCE",
            "enabled": config["enabled"],
        }

    risco_percentual = min(
        metodo["risk_percent"],
        config["max_risk_percent"],
    )
    if not math.isfinite(risco_percentual) or risco_percentual <= 0:
        return {
            "ok": False,
            "error": "INVALID_RISK_PERCENT",
            "enabled": config["enabled"],
        }

    context_mode = pre_operacao.get("context_mode") or "TENDENCIA"
    if context_mode == "CORRECAO":
        risco_percentual *= config["correction_risk_factor"]
    risco_valor = saldo * (risco_percentual / 100)
    lote_bruto = risco_valor / (distancia_stop * contract_size)

    lote_normalizado = _normalizar_lote(lote_bruto, volume_step)
    if lote_normalizado is None:
        return {
            "ok": False,
            "error": "INVALID_CALCULATED_LOT",
            "enabled": config["enabled"],
        }

    lote = lote_normalizado
    lote_original = lote

    if lote < volume_min:
        risco_se_min_lot = volume_min * distancia_stop * contract_size
        risco_se_min_lot_percent = (risco_se_min_lot / saldo) * 100
        if risco_se_min_lot_percent > config["max_risk_percent"]:
            return {
                "ok": False,
                "error": "LOT_BELOW_MINIMUM_EXCEEDS_RISK",
                "enabled": config["enabled"],
                "min_lot": volume_min,
                "max_risk_percent": config["max_risk_percent"],
                "estimated_risk_percent": round(risco_se_min_lot_percent, 4),
            }
        lote = volume_min

    if lote > volume_max:
        lote = volume_max

    risco_efetivo = lote * distancia_stop * contract_size
    risco_efetivo_percent = (risco_efetivo / saldo) * 100
    lote_capado = lote != lote_original
    risco_acima_do_alvo = risco_efetivo_percent > risco_percentual

    aprovado = (
        config["enabled"]
        and risco_efetivo_percent <= config["max_risk_percent"]
        and lote <= volume_max
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
        "calculated_lot": round(lote_bruto, 4),
        "lot": lote,
        "lot_capped": lote_capado,
        "volume_step": volume_step,
        "volume_min": volume_min,
        "volume_max": volume_max,
        "contract_size": contract_size,
        "estimated_risk": round(risco_efetivo, 2),
        "estimated_risk_percent": round(risco_efetivo_percent, 4),
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
        import mt5linux_compat as mt5
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
