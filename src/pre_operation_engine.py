# ===================================
# PRE OPERATION ENGINE
# ===================================

import csv
import configparser
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from src.risk_method_engine import obter_metodo
from src.smc_entry_guard import validate_smc_entry
try:
    from src.interest_zone_engine import validate_zone_for_execution
except ImportError:
    from interest_zone_engine import validate_zone_for_execution


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
PRE_OPERATION_FILE = DATA_DIR / "pre_operation_trades.csv"
CANDLE_HISTORY_FILE = DATA_DIR / "candle_history.csv"
CONFIG_FILE = ROOT_DIR / "config.ini"

CAMPOS = [
    "id",
    "data_abertura",
    "data_fechamento",
    "ativo",
    "direcao",
    "status_setup",
    "metodo_risco",
    "context_mode",
    "entrada",
    "stop",
    "tp1",
    "tp2",
    "rr",
    "smc",
    "elliott",
    "bos",
    "choch",
    "confianca",
    "brain_score",
    "status",
    "resultado",
    "observacao",
    "region_id",
    "structural_gate_version",
    "structural_gate_timestamp",
    "structural_gate_result",
]


def _garantir_arquivo():

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if PRE_OPERATION_FILE.exists():
        return

    with PRE_OPERATION_FILE.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS, delimiter=";")
        escritor.writeheader()


def _ler_registros():

    _garantir_arquivo()

    with PRE_OPERATION_FILE.open("r", encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        return list(leitor)


def _salvar_registros(registros):

    _garantir_arquivo()

    with PRE_OPERATION_FILE.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS, delimiter=";")
        escritor.writeheader()
        for registro in registros:
            escritor.writerow({
                campo: registro.get(campo, "")
                for campo in CAMPOS
            })


def _proximo_id(registros):

    if not registros:
        return "PREOP-000001"

    ultimo = registros[-1].get("id", "PREOP-000000")

    try:
        numero = int(ultimo.split("-")[-1])
    except ValueError:
        numero = len(registros)

    return f"PREOP-{numero + 1:06d}"


def _rr_minimo_operacional():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")
    if not config.has_section("EXECUTION"):
        return 1.0
    section = config["EXECUTION"]
    laboratorio = (
        section.get("demo_only", "true").lower() == "true"
        and section.get("learning_lab_enabled", "false").lower() == "true"
    )
    if laboratorio:
        return section.getfloat("lab_min_live_rr", fallback=0.75)
    return section.getfloat("min_live_rr", fallback=1.0)


def registrar_pre_operacao(
    ativo,
    direcao,
    status_setup,
    operacao,
    smc,
    elliott,
    bos,
    choch,
    confianca,
    brain_score,
    context_mode="TENDENCIA",
    region_id="",
    bootstrap=False,
):

    registros = _ler_registros()
    smc_guard = validate_smc_entry(direcao, smc, bos, choch)
    observation_reason = smc_guard["reason"]
    if direcao == "AGUARDAR":
        observation_reason = "NO_DIRECTIONAL_SETUP"

    if not smc_guard["approved"] and not bootstrap:
        operacao = None
        status_setup = "SETUP FRACO"

    structural_gate_ok = True
    structural_gate_result = ""
    region_id_str = str(region_id or "").strip()
    if operacao is not None and direcao != "AGUARDAR" and region_id_str:
        preop_for_gate = {
            "region_id": region_id_str,
            "ativo": ativo,
        }
        gate_result = validate_zone_for_execution(preop_for_gate)
        if not gate_result.get("ok"):
            structural_gate_ok = False
            structural_gate_result = gate_result.get("error", "GATE_FAILED")
            if structural_gate_result == "PRE_OPERATION_REGION_REQUIRED":
                structural_gate_result = "NO_REGION_ID"
        else:
            structural_gate_result = "PASSED"

    if operacao is None or direcao == "AGUARDAR":
        metodo = obter_metodo()
        registro = {
            "id": _proximo_id(registros),
            "data_abertura": datetime.now().isoformat(timespec="seconds"),
            "data_fechamento": "",
            "ativo": ativo,
            "direcao": direcao,
            "status_setup": status_setup,
            "metodo_risco": metodo["name"],
            "context_mode": context_mode,
            "entrada": "",
            "stop": "",
            "tp1": "",
            "tp2": "",
            "rr": "",
            "smc": smc,
            "elliott": elliott,
            "bos": bos,
            "choch": choch,
            "confianca": confianca,
            "brain_score": brain_score,
            "status": "OBSERVADO",
            "resultado": "SEM_ENTRADA",
            "observacao": (
                "Pre-operacao registrada sem entrada simulada. "
                f"{observation_reason}."
            ),
            "region_id": region_id_str,
            "structural_gate_version": "",
            "structural_gate_timestamp": "",
            "structural_gate_result": "",
        }
    else:
        metodo = obter_metodo()
        entrada, stop, tp1, tp2, rr = operacao
        entrada = float(entrada)
        stop = float(stop)
        tp1 = float(tp1)
        tp2 = float(tp2)
        risco = abs(entrada - stop)
        retorno = abs(tp2 - entrada)
        rr = round(retorno / risco, 2) if risco > 0 else 0
        rr_minimo = _rr_minimo_operacional()

        if rr < rr_minimo:
            registro = {
                "id": _proximo_id(registros),
                "data_abertura": datetime.now().isoformat(timespec="seconds"),
                "data_fechamento": datetime.now().isoformat(timespec="seconds"),
                "ativo": ativo,
                "direcao": direcao,
                "status_setup": status_setup,
                "metodo_risco": metodo["name"],
                "context_mode": context_mode,
                "entrada": entrada,
                "stop": stop,
                "tp1": tp1,
                "tp2": tp2,
                "rr": rr,
                "smc": smc,
                "elliott": elliott,
                "bos": bos,
                "choch": choch,
                "confianca": confianca,
                "brain_score": brain_score,
                "status": "OBSERVADO",
                "resultado": "RR_TECNICO_INSUFICIENTE",
                "observacao": (
                    f"Plano nao aberto: alvo tecnico nao paga o risco. "
                    f"RR calculado 1:{rr}; piso de protecao 1:{rr_minimo}."
                ),
                "region_id": region_id_str,
                "structural_gate_version": "",
                "structural_gate_timestamp": "",
                "structural_gate_result": "",
            }
        else:
            if not structural_gate_ok:
                status_final = "OBSERVADO"
                resultado_final = structural_gate_result or "STRUCTURAL_GATE_FAILED"
                observacao_final = (
                    f"Plano nao aberto: gate estrutural recusou a regiao. "
                    f"Motivo: {structural_gate_result}."
                )
            else:
                status_final = "ABERTO"
                resultado_final = "EM_SIMULACAO"
                observacao_final = (
                    "Simulacao com stop estrutural e alvos tecnicos de liquidez. "
                    f"RR tecnico calculado: 1:{rr}."
                )
            agora = datetime.now().isoformat(timespec="seconds")
            registro = {
                "id": _proximo_id(registros),
                "data_abertura": agora,
                "data_fechamento": "" if status_final == "ABERTO" else agora,
                "ativo": ativo,
                "direcao": direcao,
                "status_setup": status_setup,
                "metodo_risco": metodo["name"],
                "context_mode": context_mode,
                "entrada": entrada,
                "stop": stop,
                "tp1": tp1,
                "tp2": tp2,
                "rr": rr,
                "smc": smc,
                "elliott": elliott,
                "bos": bos,
                "choch": choch,
                "confianca": confianca,
                "brain_score": brain_score,
                "status": status_final,
                "resultado": resultado_final,
                "observacao": (
                    "Simulacao com stop estrutural e alvos tecnicos de liquidez. "
                    f"RR tecnico calculado: 1:{rr}."
                ),
                "region_id": region_id_str,
                "structural_gate_version": "LEON_CAUSAL_CONTRACT_V2" if structural_gate_ok else "",
                "structural_gate_timestamp": agora if structural_gate_ok else "",
                "structural_gate_result": structural_gate_result,
            }
            if not structural_gate_ok:
                registro["observacao"] = observacao_final

    registros.append(registro)
    _salvar_registros(registros)

    print("PRE-OPERACAO REGISTRADA")
    print(f"ID: {registro['id']}")
    print(f"STATUS: {registro['status']}")
    print(f"RESULTADO: {registro['resultado']}")

    return registro


def invalidar_pre_operacao(pre_operation_id, resultado, observacao):

    registros = _ler_registros()
    alterado = None

    for registro in registros:
        if registro.get("id") != pre_operation_id:
            continue

        if registro.get("status") != "ABERTO":
            return {
                "ok": False,
                "error": "PRE_OPERATION_NOT_OPEN",
                "pre_operation_id": pre_operation_id,
                "status": registro.get("status"),
            }

        registro["status"] = "FECHADO"
        registro["resultado"] = resultado
        registro["data_fechamento"] = datetime.now().isoformat(timespec="seconds")
        registro["observacao"] = observacao
        alterado = registro
        break

    if alterado is None:
        return {
            "ok": False,
            "error": "PRE_OPERATION_NOT_FOUND",
            "pre_operation_id": pre_operation_id,
        }

    _salvar_registros(registros)

    return {
        "ok": True,
        "pre_operation": alterado,
    }


def reconciliar_pre_operacao_mt5(
    pre_operation_id,
    resultado,
    data_fechamento,
    observacao,
):

    registros = _ler_registros()
    alterado = None

    for registro in registros:
        if registro.get("id") != pre_operation_id:
            continue

        registro["status"] = "FECHADO"
        registro["resultado"] = resultado
        registro["data_fechamento"] = data_fechamento
        registro["observacao"] = observacao
        alterado = registro
        break

    if alterado is None:
        return {
            "ok": False,
            "error": "PRE_OPERATION_NOT_FOUND",
            "pre_operation_id": pre_operation_id,
        }

    _salvar_registros(registros)

    return {
        "ok": True,
        "pre_operation": alterado,
    }


def _ultimo_candle():

    if not CANDLE_HISTORY_FILE.exists():
        return None

    linhas = [
        linha.strip()
        for linha in CANDLE_HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]

    if not linhas:
        return None

    partes = linhas[-1].split(";")

    if len(partes) < 6:
        return None

    try:
        return {
            "data": partes[0],
            "ativo": partes[1],
            "high": float(partes[3]),
            "low": float(partes[4]),
            "close": float(partes[5]),
        }
    except ValueError:
        return None


def avaliar_pre_operacoes_abertas():

    registros = _ler_registros()
    candle = _ultimo_candle()

    if candle is None:
        return {
            "ok": False,
            "error": "NO_CANDLE_TO_EVALUATE_PRE_OPERATION",
        }

    alterados = 0
    resultados = []

    for registro in registros:
        if registro.get("status") != "ABERTO":
            continue

        try:
            data_abertura = datetime.fromisoformat(registro["data_abertura"])
            data_candle = datetime.fromisoformat(candle["data"])
        except ValueError:
            data_abertura = None
            data_candle = None

        if (
            data_abertura
            and data_candle
            and data_candle <= data_abertura + timedelta(seconds=60)
        ):
            continue

        try:
            stop = float(registro["stop"])
            tp1 = float(registro["tp1"])
            tp2 = float(registro["tp2"])
        except ValueError:
            continue

        direcao = registro.get("direcao")
        resultado = None

        if direcao == "COMPRA":
            if candle["low"] <= stop:
                resultado = "LOSS"
            elif candle["high"] >= tp2:
                resultado = "WIN_TP2"
            elif candle["high"] >= tp1:
                resultado = "WIN_TP1"

        elif direcao == "VENDA":
            if candle["high"] >= stop:
                resultado = "LOSS"
            elif candle["low"] <= tp2:
                resultado = "WIN_TP2"
            elif candle["low"] <= tp1:
                resultado = "WIN_TP1"

        if resultado is None:
            continue

        registro["status"] = "FECHADO"
        registro["resultado"] = resultado
        registro["data_fechamento"] = datetime.now().isoformat(timespec="seconds")
        registro["observacao"] = f"Avaliado pelo candle {candle['data']}."
        alterados += 1
        resultados.append({
            "id": registro.get("id"),
            "resultado": resultado,
            "data_abertura": registro.get("data_abertura"),
            "data_fechamento": registro.get("data_fechamento"),
            "ativo": registro.get("ativo"),
            "direcao": registro.get("direcao"),
            "status_setup": registro.get("status_setup"),
            "entrada": registro.get("entrada"),
            "stop": registro.get("stop"),
            "tp1": registro.get("tp1"),
            "tp2": registro.get("tp2"),
            "rr": registro.get("rr"),
            "smc": registro.get("smc"),
            "elliott": registro.get("elliott"),
            "bos": registro.get("bos"),
            "choch": registro.get("choch"),
            "confianca": registro.get("confianca"),
            "brain_score": registro.get("brain_score"),
            "candle": candle,
        })

    if alterados:
        _salvar_registros(registros)

    return {
        "ok": True,
        "updated": alterados,
        "results": resultados,
    }


def resumo_pre_operacao():

    registros = _ler_registros()

    simulacoes = [
        r
        for r in registros
        if r.get("resultado") != "SEM_ENTRADA"
    ]
    observacoes = [
        r
        for r in registros
        if r.get("resultado") == "SEM_ENTRADA"
    ]
    fechados = [r for r in registros if r.get("status") == "FECHADO"]
    abertos = [r for r in registros if r.get("status") == "ABERTO"]
    wins = [r for r in fechados if str(r.get("resultado", "")).startswith("WIN")]
    losses = [r for r in fechados if r.get("resultado") == "LOSS"]

    taxa = 0
    if fechados:
        taxa = round((len(wins) / len(fechados)) * 100, 2)
    decididos = len(wins) + len(losses)
    win_rate_decidido = (
        round((len(wins) / decididos) * 100, 2)
        if decididos
        else 0
    )

    ultimo = registros[-1] if registros else None

    return {
        "total": len(registros),
        "observacoes": len(observacoes),
        "simulacoes": len(simulacoes),
        "abertos": len(abertos),
        "fechados": len(fechados),
        "wins": len(wins),
        "losses": len(losses),
        "taxa": taxa,
        "decididos": decididos,
        "win_rate_decidido": win_rate_decidido,
        "ultimo": ultimo,
    }
