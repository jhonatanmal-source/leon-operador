# ===================================
# DAILY OPERATOR REPORT
# ===================================

import configparser
import csv
from datetime import date, datetime
from pathlib import Path

from operation_report import registros_operacao_do_dia


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
REPORTS_DIR = ROOT_DIR / "reports"

PRE_OPERATION_FILE = DATA_DIR / "pre_operation_trades.csv"
LOG_FILE = LOGS_DIR / "leon_log.txt"
ERROR_FILE = LOGS_DIR / "errors.txt"
DAILY_OPERATOR_REPORT_FILE = REPORTS_DIR / "daily_operator_report.txt"
CONFIG_FILE = ROOT_DIR / "config.ini"


def _linhas_arquivo(caminho):

    if not caminho.exists():
        return []

    return caminho.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()


def _linhas_do_dia(caminho, data):

    prefixo_log = f"[{data.isoformat()}"
    prefixo_iso = data.isoformat()

    return [
        linha
        for linha in _linhas_arquivo(caminho)
        if linha.startswith(prefixo_log) or linha.startswith(prefixo_iso)
    ]


def _pre_operacoes_do_dia(data):

    if not PRE_OPERATION_FILE.exists():
        return []

    with PRE_OPERATION_FILE.open("r", encoding="utf-8", newline="") as arquivo:
        return [
            registro
            for registro in csv.DictReader(arquivo, delimiter=";")
            if str(registro.get("data_abertura", "")).startswith(data.isoformat())
        ]


def _primeiro_inicio_operador(logs):

    for linha in logs:
        if "PROFESSOR LEON | operador iniciado" in linha:
            return linha.split("]")[0].replace("[", "")

    inicios = [
        linha
        for linha in _linhas_arquivo(LOG_FILE)
        if "PROFESSOR LEON | operador iniciado" in linha
    ]

    if inicios:
        return (
            inicios[-1]
            .split("]")[0]
            .replace("[", "")
            + " (ciclo iniciado anteriormente)"
        )

    return "SEM REGISTRO"


def _contar(registros, campo, valor):

    return len([
        registro
        for registro in registros
        if registro.get(campo) == valor
    ])


def _contar_contendo(linhas, texto):

    return len([linha for linha in linhas if texto in linha])


def _timestamp_linha(linha):

    texto = linha.strip()

    if texto.startswith("[") and "]" in texto:
        texto = texto.split("]", 1)[0].lstrip("[")
    elif " | " in texto:
        texto = texto.split(" | ", 1)[0]
    else:
        return None

    try:
        return datetime.fromisoformat(texto)
    except ValueError:
        return None


def _ultimo_timestamp(linhas, marcadores):

    ultimo = None

    for linha in linhas:
        if not any(marcador in linha for marcador in marcadores):
            continue

        timestamp = _timestamp_linha(linha)
        if timestamp and (ultimo is None or timestamp > ultimo):
            ultimo = timestamp

    return ultimo


def _classificar_erros_do_dia(erros, logs):

    ultimo_sucesso_analise = _ultimo_timestamp(
        logs,
        ["OPERATOR | analise programada executada"],
    )
    ultimo_sucesso_telegram = _ultimo_timestamp(
        logs,
        [
            "TELEGRAM | mensagem enviada com sucesso",
            "TELEGRAM | foto enviada com sucesso",
            "OPERATOR | status Telegram enviado",
        ],
    )
    ativos = []
    recuperados = []

    for linha in erros:
        timestamp = _timestamp_linha(linha)
        texto = linha.lower()
        recuperado = False

        if (
            timestamp
            and "falha na analise" in texto
            and ultimo_sucesso_analise
            and timestamp < ultimo_sucesso_analise
        ):
            recuperado = True

        if (
            timestamp
            and "telegram" in texto
            and ultimo_sucesso_telegram
            and timestamp < ultimo_sucesso_telegram
        ):
            recuperado = True

        (recuperados if recuperado else ativos).append(linha)

    return ativos, recuperados


def _config_score():

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")
    normal = config.getint("RISK", "min_setup_score", fallback=70)
    laboratorio_ativo = (
        config.getboolean("EXECUTION", "demo_only", fallback=True)
        and config.getboolean(
            "EXECUTION",
            "learning_lab_enabled",
            fallback=False,
        )
    )
    laboratorio = config.getint(
        "EXECUTION",
        "lab_min_setup_score",
        fallback=60,
    )
    return laboratorio if laboratorio_ativo else normal


def gerar_relatorio_operador_diario(data=None):

    data = data or date.today()
    logs = _linhas_do_dia(LOG_FILE, data)
    erros = _linhas_do_dia(ERROR_FILE, data)
    erros_ativos, erros_recuperados = _classificar_erros_do_dia(erros, logs)
    preops = _pre_operacoes_do_dia(data)
    decisoes = registros_operacao_do_dia(data)
    score_minimo = _config_score()

    checkpoints = _contar_contendo(logs, "OPERATOR | status Telegram enviado")
    estudos = len(preops)
    setups_a_plus = len([
        registro
        for registro in preops
        if registro.get("status_setup") in ["SETUP A+", "SETUP PREMIUM"]
    ])
    setups_bloqueados = len([
        registro
        for registro in preops
        if registro.get("direcao") == "AGUARDAR"
        or registro.get("resultado") == "SEM_ENTRADA"
        or registro.get("status_setup") == "SETUP FRACO"
    ])

    bloqueios_rr = len([
        registro
        for registro in decisoes
        if "RR" in str(registro.get("motivo", "")).upper()
        or str(registro.get("motivo", "")).upper() == "LIVE_RR_BELOW_MINIMUM"
    ])
    bloqueios_brain_registrados = [
        registro
        for registro in decisoes
        if "BRAIN" in str(registro.get("motivo", "")).upper()
        or str(registro.get("motivo", "")).upper() == "SETUP_SCORE_BELOW_MINIMUM"
    ]
    bloqueios_brain_atuais = len([
        registro
        for registro in bloqueios_brain_registrados
        if float(registro.get("brain_score") or 0) < score_minimo
    ])
    bloqueios_brain_legados = (
        len(bloqueios_brain_registrados) - bloqueios_brain_atuais
    )
    bloqueios_zona = len([
        registro
        for registro in decisoes
        if "ZONA" in str(registro.get("motivo", "")).upper()
        or "DRIFT" in str(registro.get("motivo", "")).upper()
    ])

    entradas = _contar(decisoes, "decisao", "ENTRAR")
    bloqueios = _contar(decisoes, "decisao", "BLOQUEAR")
    observacoes = _contar(decisoes, "decisao", "OBSERVAR")

    if bloqueios_brain_atuais:
        melhoria = "Buscar mais confluencia para elevar Brain Score antes de liberar demo."
    elif bloqueios_rr:
        melhoria = "Priorizar entradas mais proximas da zona para preservar RR real."
    elif bloqueios_zona:
        melhoria = "Evitar perseguir preco depois da zona planejada."
    elif setups_a_plus == 0:
        melhoria = "Continuar estudando ate aparecer Setup A+ com confluencia limpa."
    else:
        melhoria = "Revisar prints e resultados das operacoes para fortalecer criterios."

    relatorio = "\n".join([
        "LEON | RELATORIO OPERACIONAL DIARIO",
        "=================================",
        f"Data: {data.isoformat()}",
        f"Inicio do operador: {_primeiro_inicio_operador(logs)}",
        "",
        "Resumo",
        f"- Checkpoints enviados: {checkpoints}",
        f"- Estudos realizados: {estudos}",
        f"- Setups A+: {setups_a_plus}",
        f"- Setups bloqueados/observados: {setups_bloqueados}",
        "",
        "Decisoes por operacao",
        f"- Entrar: {entradas}",
        f"- Bloquear: {bloqueios}",
        f"- Observar: {observacoes}",
        "",
        "Bloqueios",
        f"- Alvo tecnico nao pagou o risco: {bloqueios_rr}",
        (
            f"- Brain Score abaixo do minimo atual ({score_minimo}): "
            f"{bloqueios_brain_atuais}"
        ),
        f"- Bloqueios de score por regra antiga: {bloqueios_brain_legados}",
        f"- Preco fora da zona: {bloqueios_zona}",
        "",
        "Erros",
        f"- Ativos: {len(erros_ativos)}",
        f"- Recuperados no mesmo dia: {len(erros_recuperados)}",
        *[f"- {linha[-220:]}" for linha in erros_ativos[-5:]],
        "",
        "Melhoria sugerida para o proximo dia",
        f"- {melhoria}",
        "=================================",
        "",
    ])

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DAILY_OPERATOR_REPORT_FILE.write_text(relatorio, encoding="utf-8")

    return relatorio


if __name__ == "__main__":

    print(gerar_relatorio_operador_diario())
