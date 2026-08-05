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
        "auto_simulate_min_winrate": 0.0,
        "consecutive_loss_limit": 5,
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
        "auto_simulate_min_winrate": secao.getfloat("auto_simulate_min_winrate", fallback=padrao["auto_simulate_min_winrate"]),
        "consecutive_loss_limit": secao.getint("consecutive_loss_limit", fallback=padrao["consecutive_loss_limit"]),
    }


def _consecutive_losses(shadows=None, limit=5):
    """Retorna True se houver 'limit' ou mais losses consecutivos nas shadows fechadas."""
    if shadows is None:
        import csv
        shadow_file = DATA_DIR / "shadow_trades.csv"
        if not shadow_file.exists():
            return False
        with shadow_file.open("r", encoding="utf-8", newline="") as f:
            shadows = list(csv.DictReader(f, delimiter=";"))

    fechados = [r for r in shadows if r.get("status") == "FECHADO"]
    recentes = fechados[-limit:]
    return len(recentes) == limit and all(r.get("result") == "LOSS" for r in recentes)


def _ler_todas_entradas_simuladas():
    """Retorna todas as linhas de simulated_entries.csv ou lista vazia."""
    arquivo = DATA_DIR / "simulated_entries.csv"
    if not arquivo.exists():
        return []
    import csv
    with arquivo.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def metrica_bias():
    """Calcula o viés COMPRA/VENDA das entradas simuladas para monitoramento."""
    linhas = _ler_todas_entradas_simuladas()
    if not linhas:
        return {"total": 0, "compra": 0, "venda": 0, "bias_ratio": 0.0, "alerta": "SEM_DADOS"}
    compras = sum(1 for r in linhas if r.get("direcao") == "COMPRA")
    vendas = sum(1 for r in linhas if r.get("direcao") == "VENDA")
    total = compras + vendas
    bias = round(compras / total * 100, 1) if total else 0.0
    alerta = "OK" if 30 <= bias <= 70 else "VIES_ALTO"
    return {
        "total": total,
        "compra": compras,
        "venda": vendas,
        "bias_ratio": bias,
        "alerta": alerta,
    }


def registrar_entrada_simulada(direcao, entry, stop, tp, brain_score, contexto):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    arquivo = DATA_DIR / "simulated_entries.csv"
    cabecalho = ["id", "data", "direcao", "entry", "stop", "tp", "brain_score", "contexto", "resultado"]
    if not arquivo.exists():
        with arquivo.open("w", encoding="utf-8", newline="") as f:
            import csv
            csv.writer(f, delimiter=";").writerow(cabecalho)
    with arquivo.open("a", encoding="utf-8", newline="") as f:
        import csv
        linha_id = f"SIM-{datetime.now().strftime('%Y%m%d%H%M%S')}-{abs(hash(direcao + str(datetime.now().timestamp()))) % 100000:05d}"
        csv.writer(f, delimiter=";").writerow([linha_id, datetime.now().isoformat(timespec="seconds"), direcao, entry, stop, tp, brain_score, contexto, ""])


def avaliar_entradas_simuladas(candles):
    """Avalia entradas simuladas abertas contra candles recentes.
    
    Similar a evaluate_shadow_trades, mas para simulated_entries.
    Retorna quantas foram atualizadas.
    """
    if not candles:
        return {"ok": False, "error": "NO_CANDLES"}

    arquivo = DATA_DIR / "simulated_entries.csv"
    if not arquivo.exists():
        return {"ok": False, "error": "NO_SIMULATED_ENTRIES"}

    import csv
    with arquivo.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = list(reader)

    if not rows:
        return {"ok": False, "error": "EMPTY_FILE"}

    updated = 0
    for row in rows:
        if row.get("resultado", ""):
            continue  # ja avaliado

        entrada_data = row.get("data", "")
        if not entrada_data:
            continue

        direcao = row.get("direcao", "")
        try:
            entry = float(row.get("entry", 0))
            stop = float(row.get("stop", 0))
            tp = float(row.get("tp", 0))
        except (ValueError, TypeError):
            continue

        if direcao not in ("COMPRA", "VENDA") or stop == 0 or tp == 0:
            continue

        # avaliar contra candles posteriores a entrada
        for candle in candles:
            candle_time = str(candle.get("time", ""))
            if candle_time <= entrada_data:
                continue

            try:
                high = float(candle.get("high", 0))
                low = float(candle.get("low", 0))
            except (ValueError, TypeError):
                continue

            stop_hit = (
                low <= stop if direcao == "COMPRA"
                else high >= stop
            )
            target_hit = (
                high >= tp if direcao == "COMPRA"
                else low <= tp
            )

            if stop_hit or target_hit:
                row["resultado"] = "LOSS" if stop_hit else "WIN_2R"
                updated += 1
                break
        else:
            # nenhum candle posterior atingiu stop ou tp
            pass

    # reescrever arquivo com resultados atualizados
    with arquivo.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    return {"ok": True, "updated": updated}


def _winrate_shadows_recentes(ultimas_n=20):
    """Calcula winrate das últimas N shadow trades fechadas.

    Usado pelo bootstrap para decidir se continua simulando.
    Se winrate muito baixa, o bootstrap pausa para evitar perdas em sequência.
    """
    import csv
    shadow_file = DATA_DIR / "shadow_trades.csv"
    if not shadow_file.exists():
        return {"winrate": 0, "fechados": 0, "wins": 0, "losses": 0}

    with shadow_file.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))

    fechados = [r for r in rows if r.get("status") == "FECHADO"][-ultimas_n:]
    if not fechados:
        return {"winrate": 0, "fechados": 0, "wins": 0, "losses": 0}

    wins = sum(1 for r in fechados if str(r.get("result") or "").startswith("WIN"))
    losses = sum(1 for r in fechados if r.get("result") == "LOSS")
    total = wins + losses
    winrate = round(wins / total * 100, 1) if total else 0

    return {"winrate": winrate, "fechados": total, "wins": wins, "losses": losses}


def auto_simulate_permitido(brain_score=0, winrate_min=None):
    """Verifica se o bootstrap pode fazer auto-simulate.

    Critérios:
    - brain_score >= auto_simulate_min_score
    - Nenhuma streak de perdas consecutivas >= consecutive_loss_limit
    - winrate das últimas shadows >= auto_simulate_min_winrate (se houver dados)
    - Sem dados de winrate (0 fechados) → permite (fase inicial de coleta)
    """
    limiares = obter_limiares()
    if not limiares["auto_simulate_on_weak_setup"]:
        return False, "AUTO_SIMULATE_DISABLED"

    # Verificar streak de perdas consecutivas
    streak_limit = limiares.get("consecutive_loss_limit", 5)
    if _consecutive_losses(limit=streak_limit):
        return False, f"CONSECUTIVE_LOSSES ({streak_limit})"

    if int(brain_score or 0) < limiares["auto_simulate_min_score"]:
        return False, f"BRAIN_SCORE_BAIXO ({brain_score} < {limiares['auto_simulate_min_score']})"

    wr_min = winrate_min if winrate_min is not None else limiares.get("auto_simulate_min_winrate", 30)
    recente = _winrate_shadows_recentes(ultimas_n=20)

    # Sem dados fechados ainda → permite (fase de coleta)
    if recente["fechados"] == 0:
        return True, "SEM_DADOS_AINDA"

    if recente["winrate"] < wr_min:
        return False, (
            f"WINRATE_BAIXA ({recente['winrate']}% < {wr_min}%) "
            f"nas últimas {recente['fechados']} shadows "
            f"({recente['wins']}W/{recente['losses']}L)"
        )

    return True, f"OK ({recente['winrate']}% em {recente['fechados']} shadows)"


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
