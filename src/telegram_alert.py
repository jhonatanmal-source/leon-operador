# ===================================
# TELEGRAM ALERT
# ===================================

import json
from pathlib import Path

from src.market_context_agent import revisar_contextos
from src.operator_council import avaliar_conselho_operadores
from src.operator_status import obter_status_operadores
from src.operation_readiness import avaliar_prontidao_operacional
from src.pre_operation_engine import resumo_pre_operacao
from src.risk_control_agent import calcular_plano_risco, resumo_risco
from src.telegram_engine import enviar_mensagem
from src.top_down_agent import ultima_leitura_top_down


ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT_DIR / "reports"
DATA_DIR = ROOT_DIR / "data"
STRUCTURE_ALERT_STATE_FILE = DATA_DIR / "structure_alert_state.json"


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


def _linha(label, valor):

    return f"- {label}: {valor if valor not in [None, ''] else 'SEM DADOS'}"


def _bloco(titulo):

    return f"[ {titulo} ]"


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


def enviar_alerta():

    return _enviar(
        "LEON ALERTA OPERACIONAL",
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
        "LEON ALERTA BOS",
        [
            f"Ativo: {ativo}",
            f"Timeframe: {timeframe}",
            f"BOS: {bos}",
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
        "LEON ALERTA CHOCH",
        [
            f"Ativo: {ativo}",
            f"Timeframe: {timeframe}",
            f"CHOCH: {choch}",
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

    return _enviar(
        "LEON SETUP APROVADO",
        [
            f"Ativo: {ativo}",
            f"Status: {status_setup}",
            f"Direcao: {direcao}",
            f"Confianca: {confianca}",
            f"SMC: {smc}",
            f"Elliott: {elliott}",
            f"BOS: {bos}",
            f"CHOCH: {choch}",
            f"Brain Score: {brain_score}",
        ],
    )


def enviar_relatorio_diario():

    return enviar_relatorio_arquivo(
        "LEON RELATORIO DIARIO",
        REPORTS_DIR / "daily_report.txt",
    )


def enviar_relatorio_semanal():

    return enviar_relatorio_arquivo(
        "LEON RELATORIO SEMANAL",
        REPORTS_DIR / "WEEKLY_REPORT_01.txt",
    )


def enviar_relatorio_aprendizado_diario():

    return enviar_relatorio_arquivo(
        "LEON APRENDIZADO DIARIO",
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
        "LEON APRENDIZADO DIARIO",
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
        "LEON ERRO DO SISTEMA",
        [
            f"Contexto: {contexto}",
            f"Erro: {erro}",
        ],
    )


def enviar_alerta_operador_encerrado(autonomia):

    return _enviar(
        "LEON OPERADOR ENCERRADO",
        [
            _linha("Motivo", autonomia.get("reason")),
            _linha("Escopo", autonomia.get("scope")),
            _linha("Expirou em", autonomia.get("expires_at")),
            "",
            "O LEON parou com seguranca porque a autonomia terminou.",
            "Para voltar a coletar, analisar e enviar checkpoints, conceda nova autonomia.",
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
    plano_risco = None

    ultimo_pre = pre_operacao.get("ultimo") or {}
    if ultimo_pre.get("status") == "ABERTO":
        plano_risco = calcular_plano_risco(ultimo_pre)

    return _enviar(
        "LEON XAU AI | CHECKPOINT OPERACIONAL",
        [
            _linha("Horario", status["generated_at"]),
            _linha("Semaforo", prontidao.get("nivel")),
            "",
            _bloco("MERCADO"),
            _linha("Preco", coletor.get("last_price", {}).get("bid")),
            _linha("Tendencia", estrutura.get("tendencia")),
            _linha("Top-down", top_down.get("alinhamento")),
            "",
            _bloco("LEITURA ATUAL"),
            _linha("Direcao", setup.get("direcao")),
            _linha("SMC", setup.get("smc")),
            _linha("Elliott", setup.get("elliott")),
            _linha("Confianca", setup.get("confianca")),
            "",
            _bloco("OPERACOES DEMO"),
            _linha("Abertas", pre_operacao.get("abertos")),
            _linha("Concluidas", pre_operacao.get("fechados")),
            _linha("Taxa", f"{pre_operacao.get('taxa')}%"),
            _linha("Decisao", conselho.get("decision")),
            "",
            _bloco("GESTAO"),
            _linha("Risco por entrada", f"{risco_controle.get('method_risk_percent')}%"),
            _linha("Limite diario", f"{risco_controle.get('method_daily_loss_percent')}%"),
            _linha("Alvo", "TECNICO SMC"),
            "",
            _bloco("PROFESSOR LEON"),
            _linha("Emocao", professor.get("emotion", {}).get("emotion")),
            _linha("Pensamento", professor.get("emotion", {}).get("message")),
            _linha("Ultima licao", contexto.get("last_lesson") or "Em observacao"),
            "",
            _linha("Proximo envio", telegram.get("next_heartbeat")),
        ],
    )


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
        "LEON XAU AI | ALERTA DE CONFLITO",
        [
            "--------------------",
            _linha("Horario", status["generated_at"]),
            "",
            "A leitura operacional nao esta alinhada.",
            "",
            _linha("Tendencia", estrutura.get("tendencia")),
            _linha("SMC", setup.get("smc")),
            _linha("Elliott", setup.get("elliott")),
            _linha("Direcao do plano", setup.get("direcao")),
            "",
            _linha("Resumo", alinhamento.get("summary")),
            "",
            "Acao sugerida: observar e aguardar confirmacao mais limpa.",
            "--------------------",
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
        "LEON XAU AI | COLETA ANTIGA",
        [
            "--------------------",
            _linha("Horario", status["generated_at"]),
            "",
            "A coleta existe, mas nao esta recente.",
            "",
            _linha("Ultimo preco", ultimo_preco.get("bid")),
            _linha("Idade preco", ultimo_preco.get("idade")),
            _linha("Ultimo candle", ultimo_candle.get("close")),
            _linha("Idade candle", ultimo_candle.get("idade")),
            "",
            "Acao sugerida: verificar coletor, MT5 ou conexao antes de confiar no contexto.",
            "--------------------",
        ],
    )

