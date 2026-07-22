# ===================================
# TELEGRAM ALERT V2
# Mensagens tecnicas com visual limpo
# ===================================

import csv
import json
from datetime import datetime
from pathlib import Path

from src.market_context_agent import revisar_contextos
from src.operator_council import avaliar_conselho_operadores
from src.operator_status import obter_status_operadores
from src.operation_readiness import avaliar_prontidao_operacional
from src.pre_operation_engine import resumo_pre_operacao
from src.risk_control_agent import calcular_plano_risco, resumo_risco
from src.telegram_engine import enviar_mensagem, enviar_foto
from src.top_down_agent import ultima_leitura_top_down


ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT_DIR / "reports"
DATA_DIR = ROOT_DIR / "data"
STRUCTURE_ALERT_STATE_FILE = DATA_DIR / "structure_alert_state.json"


# ─── utilitarios de formatacao ───────────────────────────


def _fmt(valor, padrao="--"):
    if valor is None or valor == "" or valor == "None":
        return padrao
    return str(valor)


def _preco(valor):
    if valor is None:
        return "--"
    try:
        return f"{float(valor):.2f}"
    except (ValueError, TypeError):
        return str(valor)


def _status_emoji(status):
    mapa = {
        "PRONTO": "\u2705",
        "ATIVO": "\u2705",
        "AUTONOMO": "\u2705",
        "PROTEGENDO": "\u2705",
        "ALINHADO": "\u2705",
        "OBSERVANDO": "\U0001f7e1",
        "ATENCAO": "\u26a0\ufe0f",
        "CONFLITO": "\u274c",
        "DADOS ANTIGOS": "\u274c",
        "SEM DADOS": "\u2753",
        "DESLIGADO": "\u26aa",
        "OK": "\u2705",
        "NEUTRO": "\u26aa",
        "BULLISH": "\U0001f7e2",
        "BEARISH": "\U0001f534",
        "ALTA": "\U0001f7e2",
        "BAIXA": "\U0001f534",
        "LATERAL": "\u26aa",
        "AGUARDAR": "\u23f3",
        "COMPRA": "\U0001f7e2",
        "VENDA": "\U0001f534",
        "SETUP PREMIUM": "\U0001f451",
        "SETUP A+": "\u2b50",
        "POSSIVEL SETUP": "\U0001f4c8",
        "OBSERVAR": "\U0001f50d",
        "SEM OPERACAO": "\u26aa",
        "APROVADO": "\u2705",
        "REPROVADO": "\u274c",
        "true": "\u2705",
        "True": "\u2705",
    }
    return mapa.get(status, "")


def _linha(label, valor, unidade=""):

    v = _fmt(valor)
    if unidade:
        v = f"{v} {unidade}"
    return f"\u2022 {label}: {v}"


def _linha_preco(label, valor):

    return f"\u2022 {label}: {_preco(valor)}"


def _bloco(titulo):

    return f"\n\u2501\u2501\u2501 {titulo} \u2501\u2501\u2501"


def _espaco():

    return ""


def _ler_interest_zones(limite=5):

    arquivo = DATA_DIR / "interest_zones_memory.csv"
    if not arquivo.exists():
        return []

    zonas = []
    try:
        with arquivo.open("r", encoding="utf-8") as f:
            leitor = csv.reader(f, delimiter=";")
            for linha in leitor:
                if len(linha) >= 5:
                    zonas.append({
                        "tipo": linha[0],
                        "high": linha[1],
                        "low": linha[2],
                        "forca": linha[3] if len(linha) > 3 else "",
                        "direcao": linha[4] if len(linha) > 4 else "",
                    })
    except (OSError, csv.Error):
        pass

    return zonas[-limite:]


def _ler_smc_memory(limite=3):

    arquivo = DATA_DIR / "smc_memory.csv"
    if not arquivo.exists():
        return []

    eventos = []
    try:
        with arquivo.open("r", encoding="utf-8") as f:
            leitor = csv.reader(f, delimiter=";")
            for linha in leitor:
                if len(linha) >= 3:
                    eventos.append({
                        "tipo": linha[0],
                        "preco": linha[1],
                        "time": linha[2] if len(linha) > 2 else "",
                    })
    except (OSError, csv.Error):
        pass

    return eventos[-limite:]


# ─── estrutura de envio ───────────────────────────


def _ler_estado_alertas_estrutura():

    if not STRUCTURE_ALERT_STATE_FILE.exists():
        return {}

    try:
        estado = json.loads(
            STRUCTURE_ALERT_STATE_FILE.read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return {}

    return estado if isinstance(estado, dict) else {}


def _salvar_estado_alertas_estrutura(estado):

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STRUCTURE_ALERT_STATE_FILE.write_text(
        json.dumps(estado, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _assinatura_evento_estrutura(tipo, evento):

    if not isinstance(evento, dict):
        return None

    return "|".join(
        [
            str(tipo),
            str(evento.get("time")),
            str(evento.get("level")),
            str(evento.get("close")),
        ]
    )


def _enviar_evento_estrutura(chave, assinatura, titulo, linhas):

    if assinatura is None:
        return _enviar(titulo, linhas)

    estado = _ler_estado_alertas_estrutura()
    if estado.get(chave) == assinatura:
        return {
            "ok": False,
            "error": "TELEGRAM_STRUCTURE_EVENT_ALREADY_SENT",
        }

    resultado = _enviar(titulo, linhas)
    if resultado.get("ok"):
        estado[chave] = assinatura
        _salvar_estado_alertas_estrutura(estado)

    return resultado


def _enviar(titulo, linhas):

    mensagem = "\n".join(
        [titulo, ""]
        + [str(linha) for linha in linhas if linha is not None]
    )

    return enviar_mensagem(mensagem)


def _status_visual(status):

    mapa = {
        "OK": "OK",
        "ATIVO": "OK ATIVO",
        "AUTONOMO": "OK AUTONOMO",
        "PROTEGENDO": "OK PROTEGENDO",
        "PRONTO": "OK PRONTO",
        "OBSERVANDO": "OBSERVANDO",
        "ALINHADO": "OK ALINHADO",
        "ATENCAO": "ATENCAO",
        "CONFLITO": "BLOQUEIO CONFLITO",
        "DADOS ANTIGOS": "BLOQUEIO DADOS ANTIGOS",
        "SEM DADOS": "SEM DADOS",
        "DESLIGADO": "DESLIGADO",
    }

    return mapa.get(status, status)


# ─── funcoes publicas ───────────────────────────


def enviar_alerta():

    return _enviar(
        "\u2699\ufe0f LEON \u2014 Alerta Operacional",
        [
            "Sistema preparado para envio Telegram.",
        ],
    )


def enviar_alerta_bos(ativo, timeframe, bos, evento=None):

    if bos == "SEM_BOS":
        return {
            "ok": False,
            "error": "TELEGRAM_BOS_IGNORED",
        }

    return _enviar_evento_estrutura(
        f"{ativo}|{timeframe}|BOS",
        _assinatura_evento_estrutura(bos, evento),
        f"\U0001f4c8 LEON \u2014 BOS detectado",
        [
            _linha("Ativo", ativo),
            _linha("Timeframe", timeframe),
            _linha("Tipo", bos),
            "",
            "\u2139\ufe0f BOS indica deslocamento estrutural. "
            "Aguardar CHOCH para confirmacao.",
        ],
    )


def enviar_alerta_choch(ativo, timeframe, choch, evento=None):

    if choch == "SEM_CHOCH":
        return {
            "ok": False,
            "error": "TELEGRAM_CHOCH_IGNORED",
        }

    return _enviar_evento_estrutura(
        f"{ativo}|{timeframe}|CHOCH",
        _assinatura_evento_estrutura(choch, evento),
        f"\U0001f504 LEON \u2014 CHOCH detectado",
        [
            _linha("Ativo", ativo),
            _linha("Timeframe", timeframe),
            _linha("Tipo", choch),
            "",
            "\u2139\ufe0f CHOCH sinaliza possivel mudanca de carater. "
            "Aguardar zona SMC + liquidez para entrada.",
        ],
    )


def enviar_alerta_setup(
    ativo,
    status_setup,
    direcao,
    confianca,
    smc,
    elliott,
    bos,
    choch,
    brain_score,
):

    if status_setup not in ["SETUP PREMIUM", "SETUP A+"]:
        return {
            "ok": False,
            "error": "TELEGRAM_SETUP_IGNORED",
        }

    zonas = _ler_interest_zones(3)

    linhas = [
        _linha("Ativo", ativo),
        _linha("Status", f"{_status_emoji(status_setup)} {status_setup}"),
        _linha("Direcao", f"{_status_emoji(direcao)} {direcao}"),
        _espaco(),
        _bloco("CONFIRMACOES"),
        _linha("SMC", f"{_status_emoji(smc)} {smc}"),
        _linha("Elliott", elliott),
        _linha("BOS", bos),
        _linha("CHOCH", choch),
        _linha("Confianca", f"{confianca}%"),
        _linha("Brain Score", brain_score),
    ]

    if zonas:
        linhas.extend([_espaco(), _bloco("ZONAS DE INTERESSE")])
        for i, z in enumerate(zonas, 1):
            linhas.append(
                f"  {i}. {_status_emoji(z.get('tipo'))} "
                f"{_preco(z.get('high'))} / {_preco(z.get('low'))}"
                f"  [{_fmt(z.get('forca'))}]"
            )

    return _enviar(
        f"\U0001f6a8 LEON \u2014 Setup Aprovado",
        linhas,
    )


def enviar_relatorio_diario():

    return enviar_relatorio_arquivo(
        "\U0001f4ca LEON \u2014 Relatorio Diario",
        REPORTS_DIR / "daily_report.txt",
    )


def enviar_relatorio_semanal():

    return enviar_relatorio_arquivo(
        "\U0001f4ca LEON \u2014 Relatorio Semanal",
        REPORTS_DIR / "WEEKLY_REPORT_01.txt",
    )


def enviar_relatorio_aprendizado_diario():

    return enviar_relatorio_arquivo(
        "\U0001f4da LEON \u2014 Aprendizado Diario",
        REPORTS_DIR / "daily_learning_report.txt",
    )


def enviar_relatorio_aprendizado_texto(relatorio):

    conteudo = str(relatorio or "").strip()

    if not conteudo:
        return {
            "ok": False,
            "error": "TELEGRAM_EMPTY_REPORT",
        }

    return _enviar(
        "\U0001f4da LEON \u2014 Aprendizado Diario",
        [
            conteudo[-3500:],
        ],
    )


def enviar_revisao_operacoes_texto(relatorio):

    conteudo = str(relatorio or "").strip()

    if not conteudo:
        return {
            "ok": False,
            "error": "EMPTY_OPERATION_BATCH_REVIEW",
        }

    return enviar_mensagem(conteudo[-3900:])


def enviar_relatorio_arquivo(titulo, caminho):

    if not caminho.exists():
        return {
            "ok": False,
            "error": "TELEGRAM_REPORT_NOT_FOUND",
            "details": str(caminho),
        }

    conteudo = caminho.read_text(encoding="utf-8").strip()

    if not conteudo:
        return {
            "ok": False,
            "error": "TELEGRAM_EMPTY_REPORT",
            "details": str(caminho),
        }

    return _enviar(
        titulo,
        [
            conteudo[-3500:],
        ],
    )


def enviar_erro_sistema(erro, contexto="LEON"):

    return _enviar(
        f"\u274c LEON \u2014 Erro no Sistema",
        [
            _linha("Contexto", contexto),
            _linha("Erro", erro),
        ],
    )


def enviar_alerta_operador_encerrado(autonomia):

    return _enviar(
        "\U0001f6ab LEON \u2014 Operador Encerrado",
        [
            _linha("Motivo", autonomia.get("reason")),
            _linha("Escopo", autonomia.get("scope")),
            _linha("Expirou em", autonomia.get("expires_at")),
            _espaco(),
            "O LEON parou com seguranca porque a autonomia terminou.",
            "Para voltar a operar, conceda nova autonomia.",
        ],
    )


def enviar_status_operadores():

    status = obter_status_operadores()
    operadores = status["operators"]

    coletor = operadores["collector"]
    estrutura = operadores["structure"]
    setup = operadores["setup"]
    risco = operadores["risk"]
    professor = operadores["professor"]
    telegram = operadores["telegram"]
    alinhamento = operadores["alignment"]
    pre_operacao = resumo_pre_operacao()
    prontidao = avaliar_prontidao_operacional()
    risco_controle = resumo_risco()
    conselho = avaliar_conselho_operadores()
    top_down = ultima_leitura_top_down()
    contexto = revisar_contextos()
    zonas = _ler_interest_zones(3)
    smc_eventos = _ler_smc_memory(3)
    plano_risco = None

    ultimo_pre = pre_operacao.get("ultimo") or {}
    if ultimo_pre.get("status") == "ABERTO":
        plano_risco = calcular_plano_risco(ultimo_pre)

    semaforo = prontidao.get("nivel", "")
    emoji_semaforo = {
        "VERDE": "\U0001f7e2",
        "AMARELO": "\U0001f7e1",
        "VERMELHO": "\U0001f534",
    }.get(semaforo, "\u26aa")

    linhas = [
        f"{emoji_semaforo} Semafaro: {semaforo}",
        _linha("Horario", status["generated_at"]),
        _espaco(),
        _bloco("MERCADO"),
        _linha_preco("Preco", coletor.get("last_price", {}).get("bid")),
        _linha("Tendencia", f"{_status_emoji(estrutura.get('tendencia'))} {estrutura.get('tendencia')}"),
        _linha("Top-down", top_down.get("alinhamento")),
        _linha("Sessao", coletor.get("session", {}).get("session_name")),
        _espaco(),
        _bloco("ANALISE"),
        _linha("Direcao", f"{_status_emoji(setup.get('direcao'))} {setup.get('direcao')}"),
        _linha("SMC", f"{_status_emoji(setup.get('smc'))} {setup.get('smc')}"),
        _linha("Elliott", setup.get("elliott")),
        _linha("Confianca", f"{setup.get('confianca')}%"),
        _linha("Alinhamento", f"{_status_emoji(alinhamento.get('status'))} {alinhamento.get('status')}"),
    ]

    if zonas:
        linhas.extend([_espaco(), _bloco("ZONAS")])
        for i, z in enumerate(zonas, 1):
            z_dir = z.get("direcao", z.get("tipo", ""))
            linhas.append(
                f"  {i}. {_status_emoji(z_dir)} "
                f"{_preco(z.get('high'))}-{_preco(z.get('low'))}"
                f"  [{_fmt(z.get('forca'))}]"
            )

    if smc_eventos:
        linhas.extend([_espaco(), _bloco("ESTRUTURA SMC")])
        for evt in smc_eventos:
            linhas.append(
                f"  {_status_emoji(evt.get('tipo'))} "
                f"{evt.get('tipo')} @ {_preco(evt.get('preco'))}"
            )

    linhas.extend([
        _espaco(),
        _bloco("OPERACOES"),
        _linha("Abertas", pre_operacao.get("abertos")),
        _linha("Concluidas", pre_operacao.get("fechados")),
        _linha("Taxa", f"{pre_operacao.get('taxa')}%"),
        _linha("Decisao", conselho.get("decision")),
        _espaco(),
        _bloco("RISCO"),
        _linha("Por entrada", f"{risco_controle.get('method_risk_percent')}%"),
        _linha("Limite diario", f"{risco_controle.get('method_daily_loss_percent')}%"),
        _linha("Alvo", "Tecnico SMC"),
        _espaco(),
        _bloco("PROFESSOR"),
        _linha("Estado", professor.get("emotion", {}).get("emotion")),
        _linha("Pensamento", professor.get("emotion", {}).get("message")),
        _linha("Ultima licao", contexto.get("last_lesson") or "Em observacao"),
        _espaco(),
        _linha("Proximo envio", telegram.get("next_heartbeat")),
    ])

    resultado = _enviar(
        f"\U0001f4a1 LEON XAU \u2014 Checkpoint",
        linhas,
    )

    return resultado


def enviar_alerta_conflito_operadores():

    status = obter_status_operadores()
    operadores = status["operators"]
    alinhamento = operadores["alignment"]

    if alinhamento.get("status") != "CONFLITO":
        return {
            "ok": False,
            "error": "TELEGRAM_ALIGNMENT_NOT_CONFLICT",
        }

    estrutura = operadores["structure"]
    setup = operadores["setup"]

    return _enviar(
        "\u26a0\ufe0f LEON \u2014 Conflito Operacional",
        [
            _linha("Horario", status["generated_at"]),
            _espaco(),
            "A leitura operacional nao esta alinhada:",
            _espaco(),
            _linha("Tendencia", estrutura.get("tendencia")),
            _linha("SMC", setup.get("smc")),
            _linha("Elliott", setup.get("elliott")),
            _linha("Direcao do plano", setup.get("direcao")),
            _espaco(),
            _linha("Resumo", alinhamento.get("summary")),
            _espaco(),
            "\u2139\ufe0f Acao: observar e aguardar confirmacao mais limpa.",
        ],
    )


def enviar_alerta_dados_antigos():

    status = obter_status_operadores()
    coletor = status["operators"]["collector"]

    if coletor.get("status") != "DADOS ANTIGOS":
        return {
            "ok": False,
            "error": "TELEGRAM_COLLECTOR_NOT_STALE",
        }

    ultimo_preco = coletor.get("last_price", {})
    ultimo_candle = coletor.get("last_candle", {})

    return _enviar(
        "\u274c LEON \u2014 Coleta Antiga",
        [
            _linha("Horario", status["generated_at"]),
            _espaco(),
            "A coleta existe, mas nao esta recente.",
            _espaco(),
            _linha_preco("Ultimo preco", ultimo_preco.get("bid")),
            _linha("Idade preco", ultimo_preco.get("idade")),
            _linha_preco("Ultimo candle", ultimo_candle.get("close")),
            _linha("Idade candle", ultimo_candle.get("idade")),
            _espaco(),
            "\u2139\ufe0f Verificar coletor, MT5 ou conexao antes de confiar no contexto.",
        ],
    )
