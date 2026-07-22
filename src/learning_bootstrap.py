import configparser
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "config.ini"
DATA_DIR = ROOT_DIR / "data"
BOOTSTRAP_STATE_FILE = DATA_DIR / "bootstrap_state.json"


def modo_bootstrap_ativo():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")
    if not config.has_section("BOOTSTRAP"):
        return True
    return config.get("BOOTSTRAP", "enabled", fallback="true").lower() == "true"


def obter_limiares():
    padrao = {
        "min_pre_operation_closed": 5,
        "min_pre_operation_winrate": 40.0,
        "auto_simulate_on_weak_setup": True,
        "auto_simulate_min_score": 30,
    }
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")
    if not config.has_section("BOOTSTRAP"):
        return padrao
    secao = config["BOOTSTRAP"]
    return {
        "min_pre_operation_closed": secao.getint("min_closed", fallback=padrao["min_pre_operation_closed"]),
        "min_pre_operation_winrate": secao.getfloat("min_winrate", fallback=padrao["min_pre_operation_winrate"]),
        "auto_simulate_on_weak_setup": secao.get("auto_simulate", fallback=str(padrao["auto_simulate_on_weak_setup"])).lower() == "true",
        "auto_simulate_min_score": secao.getint("auto_simulate_min_score", fallback=padrao["auto_simulate_min_score"]),
    }


def registrar_entrada_simulada(direcao, entry, stop, tp, brain_score, contexto):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    arquivo = DATA_DIR / "simulated_entries.csv"
    cabecalho = ["id", "data", "direcao", "entry", "stop", "tp", "brain_score", "contexto"]
    if not arquivo.exists():
        with arquivo.open("w", encoding="utf-8", newline="") as f:
            import csv
            csv.writer(f, delimiter=";").writerow(cabecalho)
    with arquivo.open("a", encoding="utf-8", newline="") as f:
        import csv
        linha_id = f"SIM-{datetime.now().strftime('%Y%m%d%H%M%S')}-{abs(hash(direcao + str(datetime.now().timestamp()))) % 100000:05d}"
        csv.writer(f, delimiter=";").writerow([linha_id, datetime.now().isoformat(timespec="seconds"), direcao, entry, stop, tp, brain_score, contexto])


def ler_progresso_bootstrap():
    estado = {"simulacoes_feitas": 0, "total_pre_operations": 0, "iniciou_em": None}
    from .pre_operation_engine import resumo_pre_operacao
    try:
        resumo = resumo_pre_operacao()
        estado["total_pre_operations"] = resumo["total"]
        estado["simulacoes_feitas"] = resumo["simulacoes"]
        return estado
    except Exception:
        return estado
