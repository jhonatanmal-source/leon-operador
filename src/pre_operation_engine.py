# ===================================
# PRE OPERATION ENGINE
# ===================================

import csv
import configparser
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from src.baseline_window import dentro_da_janela
from src.risk_method_engine import obter_metodo
from src.smc_entry_guard import validate_smc_entry
try:
    from src.interest_zone_engine import validate_zone_for_execution
except ImportError:
    from interest_zone_engine import validate_zone_for_execution


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DEFAULT_DATA_DIR = DATA_DIR
PRE_OPERATION_FILE = DATA_DIR / "pre_operation_trades.csv"
CANDLE_HISTORY_FILE = DATA_DIR / "candle_history.csv"
CONFIG_FILE = ROOT_DIR / "config.ini"
IDENTITY_VERSION = "LEON_PREOP_ID_V2"

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows development fallback
    fcntl = None

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
    "cycle_id",
    "analysis_id",
    "identity_version",
    "legacy_id",
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
    PRE_OPERATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    descritor, temporario = tempfile.mkstemp(
        prefix=f".{PRE_OPERATION_FILE.name}.",
        suffix=".tmp",
        dir=PRE_OPERATION_FILE.parent,
    )
    try:
        with os.fdopen(descritor, "w", encoding="utf-8", newline="") as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS, delimiter=";")
            escritor.writeheader()
            for registro in registros:
                escritor.writerow({
                    campo: registro.get(campo, "")
                    for campo in CAMPOS
                })
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, PRE_OPERATION_FILE)
        _sync_identity_registry(registros)
    except Exception:
        try:
            os.unlink(temporario)
        except OSError:
            pass
        raise


def _identity_registry_file():
    return DATA_DIR / "memory_identity_registry.json"


def _write_json_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    descritor, temporario = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
            json.dump(
                payload,
                arquivo,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            arquivo.write("\n")
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, path)
    except Exception:
        try:
            os.unlink(temporario)
        except OSError:
            pass
        raise


def _sync_identity_registry(registros):
    path = _identity_registry_file()
    payload = {
        "identity_version": IDENTITY_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "records_total": 0,
        "records": [],
    }
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass

    existing = {
        str(item.get("canonical_id") or ""): dict(item)
        for item in payload.get("records", [])
        if isinstance(item, dict) and item.get("canonical_id")
    }
    for registro in registros:
        canonical_id = str(registro.get("id") or "").strip()
        if (
            not canonical_id
            or registro.get("identity_version") != IDENTITY_VERSION
        ):
            continue
        record = existing.get(canonical_id, {})
        sources = set(record.get("sources") or [])
        sources.add("CURRENT")
        record.update({
            "canonical_id": canonical_id,
            "legacy_id": str(
                registro.get("legacy_id") or canonical_id
            ),
            "opened_at": str(registro.get("data_abertura") or ""),
            "region_id": str(registro.get("region_id") or ""),
            "closed_at": str(registro.get("data_fechamento") or ""),
            "symbol": str(registro.get("ativo") or ""),
            "direction": str(registro.get("direcao") or ""),
            "result": str(registro.get("resultado") or ""),
            "sources": sorted(sources),
            "identity_version": IDENTITY_VERSION,
        })
        record.pop("record_hash", None)
        canonical = json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        record["record_hash"] = hashlib.sha256(canonical).hexdigest()
        existing[canonical_id] = record

    records = sorted(
        existing.values(),
        key=lambda item: _numeric_id(item.get("canonical_id")),
    )
    payload.update({
        "identity_version": IDENTITY_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "records_total": len(records),
        "records": records,
    })
    _write_json_atomic(path, payload)


def _sequence_file():
    override = str(os.environ.get("LEON_PREOP_SEQUENCE_FILE") or "").strip()
    if override:
        return Path(override)
    if DATA_DIR != DEFAULT_DATA_DIR:
        return DATA_DIR / "pre_operation_sequence.json"
    return ROOT_DIR.parent / "config" / "pre_operation_sequence.json"


def _numeric_id(value):
    text = str(value or "").strip()
    if not text.startswith("PREOP-"):
        return 0
    suffix = text.rsplit("-", 1)[-1]
    return int(suffix) if suffix.isdigit() else 0


def _read_sequence(path):
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    return max(
        int(payload.get("last_value") or 0),
        _numeric_id(payload.get("last_id")),
    )


def _write_sequence(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "identity_version": IDENTITY_VERSION,
        "last_value": int(value),
        "last_id": f"PREOP-{int(value):06d}",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    descritor, temporario = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
            json.dump(payload, arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, path)
    except Exception:
        try:
            os.unlink(temporario)
        except OSError:
            pass
        raise


@contextmanager
def _sequence_lock(path):
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _proximo_id(registros):
    sequence_file = _sequence_file()
    with _sequence_lock(sequence_file):
        maximum_in_memory = max(
            (_numeric_id(registro.get("id")) for registro in registros),
            default=0,
        )
        current = max(_read_sequence(sequence_file), maximum_in_memory)
        next_value = current + 1
        _write_sequence(sequence_file, next_value)
    return f"PREOP-{next_value:06d}"


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
    new_id = _proximo_id(registros)
    smc_guard = validate_smc_entry(direcao, smc, bos, choch)
    observation_reason = smc_guard["reason"]
    if direcao == "AGUARDAR":
        observation_reason = "NO_DIRECTIONAL_SETUP"

    if not smc_guard["approved"] and not bootstrap:
        operacao = None
        status_setup = "SETUP FRACO"

    structural_gate_ok = True
    structural_gate_result = ""
    structural_region = {}
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
            structural_region = gate_result.get("region") or {}

    cycle_id = str(
        structural_region.get("cycle_id")
        or os.environ.get("LEON_CYCLE_ID")
        or ""
    )
    analysis_id = str(
        structural_region.get("analysis_id")
        or os.environ.get("LEON_ANALYSIS_ID")
        or ""
    )

    if operacao is None or direcao == "AGUARDAR":
        metodo = obter_metodo()
        registro = {
            "id": new_id,
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
                "id": new_id,
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
                "id": new_id,
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

    registro.update({
        "cycle_id": cycle_id,
        "analysis_id": analysis_id,
        "identity_version": IDENTITY_VERSION,
        "legacy_id": new_id,
    })

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


def resumo_pre_operacao(window_days=None):
    """Resumo das pre-operacoes.

    window_days: janela de dias corridos aplicada APENAS as metricas de
    desempenho (fechados/wins/losses/taxa/decididos/win_rate_decidido),
    filtrando por data_fechamento. Os campos total, abertos, simulacoes,
    observacoes e ultimo permanecem GLOBAIS para nao quebrar o estado atual
    (posicoes abertas antigas e plano de risco).

    Default None = sem filtro (compatibilidade com chamadores existentes).
    """

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

    fechados_total_global = len(fechados)
    if window_days:
        fechados = [
            r
            for r in fechados
            if dentro_da_janela(r.get("data_fechamento"), window_days)
        ]
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
        "fechados_global": fechados_total_global,
        "wins": len(wins),
        "losses": len(losses),
        "taxa": taxa,
        "decididos": decididos,
        "win_rate_decidido": win_rate_decidido,
        "window_days": window_days,
        "ultimo": ultimo,
    }
