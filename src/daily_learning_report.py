# ===================================
# DAILY LEARNING REPORT
# ===================================

import csv
from collections import Counter
from datetime import date, datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"

TRADE_MEMORY_FILE = DATA_DIR / "trade_memory.csv"
TRADE_PLAN_MEMORY_FILE = DATA_DIR / "trade_plan_memory.csv"
BRAIN_MEMORY_FILE = DATA_DIR / "brain_memory.csv"
BRAIN_CONTEXT_MEMORY_FILE = DATA_DIR / "brain_context_memory.csv"
PRICE_HISTORY_FILE = DATA_DIR / "price_history.csv"
CANDLE_HISTORY_FILE = DATA_DIR / "candle_history.csv"
SIGNALS_FILE = DATA_DIR / "signals.csv"
DAILY_LEARNING_FILE = REPORTS_DIR / "daily_learning_report.txt"


def _ler_csv(caminho, campos):

    if not caminho.exists():
        return []

    registros = []

    with caminho.open("r", encoding="utf-8", newline="") as arquivo:
        leitor = csv.reader(arquivo, delimiter=";")

        for linha in leitor:
            if not linha or linha[0].lower() in ["data", "brain_score"]:
                continue

            if len(linha) < len(campos):
                continue

            registros.append(dict(zip(campos, linha)))

    return registros


def _filtrar_por_data(registros, campo_data, data_referencia):

    filtrados = []

    for registro in registros:
        try:
            data_registro = datetime.fromisoformat(registro[campo_data]).date()
        except (KeyError, ValueError):
            continue

        if data_registro == data_referencia:
            filtrados.append(registro)

    return filtrados


def _mais_comum(registros, campo):

    valores = [
        registro.get(campo)
        for registro in registros
        if registro.get(campo)
    ]

    if not valores:
        return "SEM DADOS"

    return Counter(valores).most_common(1)[0][0]


def _media(registros, campo):

    valores = []

    for registro in registros:
        try:
            valores.append(float(registro.get(campo, 0)))
        except ValueError:
            continue

    if not valores:
        return 0

    return sum(valores) / len(valores)


def _traduzir_direcao(valor):

    traducoes = {
        "BULLISH": "ALTA",
        "BEARISH": "BAIXA",
        "COMPRADOR": "ALTA",
        "VENDEDOR": "BAIXA",
    }

    return traducoes.get(valor, valor)


def _ultimo(registros):

    if not registros:
        return {}

    return registros[-1]


def gerar_relatorio_aprendizado_diario(data_referencia=None):

    if data_referencia is None:
        data_referencia = date.today()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    memoria_trade = _ler_csv(
        TRADE_MEMORY_FILE,
        [
            "data",
            "tendencia",
            "momentum",
            "score",
            "sinal",
            "qualidade",
            "smc",
            "elliott",
            "confianca",
        ],
    )
    planos = _ler_csv(
        TRADE_PLAN_MEMORY_FILE,
        [
            "data",
            "ativo",
            "direcao",
            "smc",
            "elliott",
            "brain_score",
            "confianca",
        ],
    )
    brain = _ler_csv(
        BRAIN_MEMORY_FILE,
        [
            "brain_score",
            "confianca",
            "resultado",
        ],
    )
    brain_context = _ler_csv(
        BRAIN_CONTEXT_MEMORY_FILE,
        [
            "data",
            "origem",
            "tipo",
            "collector_status",
            "preco",
            "tendencia",
            "momentum",
            "sinal",
            "direcao",
            "smc",
            "elliott",
            "confianca",
            "brain_score",
            "alinhamento",
            "observacao",
        ],
    )
    precos = _ler_csv(
        PRICE_HISTORY_FILE,
        [
            "data",
            "ativo",
            "bid",
            "ask",
        ],
    )
    candles = _ler_csv(
        CANDLE_HISTORY_FILE,
        [
            "data",
            "ativo",
            "open",
            "high",
            "low",
            "close",
        ],
    )
    sinais = _ler_csv(
        SIGNALS_FILE,
        [
            "data",
            "tendencia",
            "momentum",
            "score",
            "sinal",
        ],
    )

    memoria_do_dia = _filtrar_por_data(
        memoria_trade,
        "data",
        data_referencia,
    )
    planos_do_dia = _filtrar_por_data(
        planos,
        "data",
        data_referencia,
    )
    precos_do_dia = _filtrar_por_data(
        precos,
        "data",
        data_referencia,
    )
    candles_do_dia = _filtrar_por_data(
        candles,
        "data",
        data_referencia,
    )
    sinais_do_dia = _filtrar_por_data(
        sinais,
        "data",
        data_referencia,
    )
    contexto_do_dia = _filtrar_por_data(
        brain_context,
        "data",
        data_referencia,
    )

    total_registros = len(memoria_do_dia)
    total_planos = len(planos_do_dia)
    total_precos = len(precos_do_dia)
    total_candles = len(candles_do_dia)
    total_sinais = len(sinais_do_dia)
    total_contextos = len(contexto_do_dia)
    smc_dominante = _mais_comum(memoria_do_dia, "smc")
    elliott_dominante = _mais_comum(memoria_do_dia, "elliott")
    confianca_dominante = _mais_comum(memoria_do_dia, "confianca")
    qualidade_dominante = _mais_comum(memoria_do_dia, "qualidade")
    direcao_dominante = _mais_comum(planos_do_dia, "direcao")
    brain_medio = _media(planos_do_dia, "brain_score")
    ultimo_preco = _ultimo(precos_do_dia)
    ultimo_candle = _ultimo(candles_do_dia)
    ultimo_sinal = _ultimo(sinais_do_dia)
    ultimo_contexto = _ultimo(contexto_do_dia)

    acertos = sum(
        1 for registro in brain
        if registro.get("resultado") == "ACERTO"
    )
    erros = sum(
        1 for registro in brain
        if registro.get("resultado") == "ERRO"
    )
    total_resultados = acertos + erros

    if total_resultados:
        taxa_acerto = (acertos / total_resultados) * 100
    else:
        taxa_acerto = 0

    linhas = [
        "=================================",
        "LEON DAILY LEARNING REPORT",
        "=================================",
        f"Data: {data_referencia}",
        "",
        "Resumo do dia",
        f"- Precos coletados: {total_precos}",
        f"- Candles coletados: {total_candles}",
        f"- Sinais registrados: {total_sinais}",
        f"- Contextos cerebrais: {total_contextos}",
        f"- Registros analisados: {total_registros}",
        f"- Planos gerados: {total_planos}",
        f"- Direcao dominante: {direcao_dominante}",
        f"- Qualidade dominante: {qualidade_dominante}",
        f"- Confianca dominante: {confianca_dominante}",
        "",
        "Ultima coleta",
        f"- Ativo: {ultimo_preco.get('ativo', 'SEM DADOS')}",
        f"- Bid: {ultimo_preco.get('bid', 'SEM DADOS')}",
        f"- Ask: {ultimo_preco.get('ask', 'SEM DADOS')}",
        f"- Candle close: {ultimo_candle.get('close', 'SEM DADOS')}",
        "",
        "Ultima leitura estrutural",
        f"- Tendencia: {_traduzir_direcao(ultimo_sinal.get('tendencia', 'SEM DADOS'))}",
        f"- Score: {ultimo_sinal.get('score', 'SEM DADOS')}",
        f"- Sinal: {ultimo_sinal.get('sinal', 'SEM DADOS')}",
        "",
        "Leitura SMC + Elliott",
        f"- SMC dominante: {smc_dominante}",
        f"- Elliott dominante: {elliott_dominante}",
        f"- Brain Score medio dos planos: {brain_medio:.2f}",
        "",
        "Ultimo contexto do cerebro",
        f"- Origem: {ultimo_contexto.get('origem', 'SEM DADOS')}",
        f"- Tipo: {ultimo_contexto.get('tipo', 'SEM DADOS')}",
        f"- Alinhamento: {ultimo_contexto.get('alinhamento', 'SEM DADOS')}",
        f"- Observacao: {ultimo_contexto.get('observacao', 'SEM DADOS')}",
        "",
        "Memoria geral do cerebro",
        f"- Acertos registrados: {acertos}",
        f"- Erros registrados: {erros}",
        f"- Taxa historica de acerto: {taxa_acerto:.2f}%",
        "",
        "Aprendizado do LEON",
        _gerar_aprendizado(
            total_registros,
            total_precos,
            total_candles,
            total_sinais,
            smc_dominante,
            elliott_dominante,
            confianca_dominante,
            qualidade_dominante,
        ),
        "=================================",
    ]

    relatorio = "\n".join(linhas)

    with DAILY_LEARNING_FILE.open("a", encoding="utf-8") as arquivo:
        arquivo.write(relatorio)
        arquivo.write("\n\n")

    print(relatorio)

    return relatorio


def _gerar_aprendizado(
    total_registros,
    total_precos,
    total_candles,
    total_sinais,
    smc_dominante,
    elliott_dominante,
    confianca_dominante,
    qualidade_dominante,
):

    if total_registros == 0 and (total_precos > 0 or total_candles > 0):
        return (
            "- Hoje houve coleta de mercado, mas ainda nao houve novo setup "
            "registrado na memoria operacional."
        )

    if total_registros == 0 and total_sinais > 0:
        return (
            "- Hoje houve leitura de sinal, mas nenhum plano operacional novo "
            "foi registrado."
        )

    if total_registros == 0:
        return "- Hoje nao houve dados suficientes para aprendizado operacional."

    if smc_dominante in ["BULLISH", "BEARISH"] and elliott_dominante in [
        "ONDA 3",
        "ONDA C",
    ]:
        return (
            "- O LEON reforcou que setups fortes aparecem quando SMC e "
            "Elliott apontam juntos."
        )

    if qualidade_dominante == "CONFLITO" or confianca_dominante == "BAIXA":
        return (
            "- O LEON registrou ambiente de conflito e deve preservar "
            "paciencia operacional."
        )

    return (
        "- O LEON acumulou contexto para comparar SMC, Elliott e confianca "
        "nos proximos ciclos."
    )


if __name__ == "__main__":

    gerar_relatorio_aprendizado_diario()
