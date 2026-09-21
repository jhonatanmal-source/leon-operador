# ===================================
# MT5 ORDER EXECUTOR
# ===================================

import configparser
import csv
from datetime import datetime
from pathlib import Path

from src.error_logger import registrar_erro
from src.log_engine import registrar_log
from src.brain_context_memory import registrar_contexto_cerebro
from src.operator_council import avaliar_conselho_operadores
from src.operation_report import registrar_relatorio_operacao
from src.pre_operation_engine import invalidar_pre_operacao
from src.risk_control_agent import (
    avaliar_limite_perda_diaria,
    avaliar_orcamento_risco_aberto,
    calcular_plano_risco,
)
from src.telegram_engine import enviar_foto, enviar_mensagem
from src.telegram_alert import enviar_erro_sistema
from src.mt5_window_snapshot import capturar_print_mt5
from src.trade_chart_snapshot import gerar_print_entrada
from src.market_context_agent import identificar_sessao
from src.news_shield import avaliar_news_shield
from src.operational_study_engine import validate_setup_a_plus, score_operational_context
from src.smc_entry_guard import validate_smc_entry
from src.top_down_agent import ultima_leitura_top_down
from src.autonomy_guard import status_autonomia
from src.multidegree_context import evaluate_daytrade_context
from src.interest_zone_engine import validate_zone_for_execution
from src.ftmo_guard import avaliar_guard_ftmo
from src.operational_evidence import validate_setup_evidence, learning_score, learning_statistics, atomic_json, VERSION
from src.memory_context_engine import avaliar_consciencia_operacional

# _mt5_exec is resolved dynamically inside executar_ordem_mt5_pre_operacao()
# to allow test mocking. It is not imported at module level.


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "config.ini"
DATA_DIR = ROOT_DIR / "data"
ORDER_MEMORY_FILE = DATA_DIR / "mt5_order_memory.csv"
PRE_OPERATION_FILE = DATA_DIR / "pre_operation_trades.csv"

ORDER_FIELDS = [
    "data",
    "pre_operation_id",
    "ativo",
    "direcao",
    "lote",
    "entrada",
    "stop",
    "tp",
    "status",
    "retcode",
    "ticket",
    "motivo",
]


def _execution_config():

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if not config.has_section("EXECUTION"):
        return {
            "enabled": False,
            "demo_only": True,
            "learning_lab_enabled": False,
            "lot": 0.01,
            "deviation": 20,
            "magic": 20260616,
            "max_spread": 1.0,
            "max_demo_orders_day": 3,
            "min_live_rr": 1.0,
            "max_entry_drift_points": 1.0,
            "lab_min_setup_score": 60,
            "lab_min_live_rr": 0.75,
            "lab_max_entry_drift_points": 3.0,
            "max_open_positions": 2,
        }

    section = config["EXECUTION"]

    return {
        "enabled": section.get("enabled", "false").lower() == "true",
        "demo_only": section.get("demo_only", "true").lower() == "true",
        "learning_lab_enabled": (
            section.get("learning_lab_enabled", "false").lower() == "true"
        ),
        "lot": section.getfloat("lot", fallback=0.01),
        "percentage_sizing": config.getboolean("RISK_CONTROL", "percentage_sizing", fallback=False),
        "deviation": section.getint("deviation", fallback=20),
        "magic": section.getint("magic", fallback=20260616),
        "max_spread": section.getfloat("max_spread", fallback=1.0),
        "max_demo_orders_day": section.getint("max_demo_orders_day", fallback=3),
        "min_live_rr": section.getfloat("min_live_rr", fallback=1.0),
        "max_entry_drift_points": section.getfloat(
            "max_entry_drift_points",
            fallback=1.0,
        ),
        "lab_min_setup_score": section.getint(
            "lab_min_setup_score",
            fallback=60,
        ),
        "lab_min_live_rr": section.getfloat(
            "lab_min_live_rr",
            fallback=0.75,
        ),
        "lab_max_entry_drift_points": section.getfloat(
            "lab_max_entry_drift_points",
            fallback=3.0,
        ),
        "max_open_positions": section.getint(
            "max_open_positions",
            fallback=2,
        ),
    }


def _risk_gate_config():

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if not config.has_section("RISK"):
        return {
            "min_setup_score": 70,
        }

    return {
        "min_setup_score": config["RISK"].getint(
            "min_setup_score",
            fallback=70,
        ),
    }


def _validar_lote_executor(plano_risco, config, symbol_info=None):
    import math

    lot = plano_risco.get("lot")
    risk_percent = plano_risco.get("estimated_risk_percent")

    if lot is None:
        return {"ok": False, "error": "INVALID_LOT", "reason": "lot is None"}

    if isinstance(lot, bool):
        return {"ok": False, "error": "INVALID_LOT", "reason": "lot is bool"}

    if isinstance(lot, str):
        return {"ok": False, "error": "INVALID_LOT", "reason": "lot is string"}

    try:
        lot_float = float(lot)
    except (TypeError, ValueError):
        return {"ok": False, "error": "INVALID_LOT", "reason": "lot not numeric"}

    if not math.isfinite(lot_float):
        return {"ok": False, "error": "INVALID_LOT", "reason": "lot not finite"}

    if lot_float <= 0:
        return {"ok": False, "error": "INVALID_LOT", "reason": "lot <= 0"}

    volume_step = 0.01
    volume_min = 0.01
    volume_max = config.get("lot", 0.01)

    if symbol_info is not None:
        vs = getattr(symbol_info, "volume_step", None)
        if vs is not None:
            try:
                volume_step = float(vs)
            except (TypeError, ValueError):
                pass
        vmin = getattr(symbol_info, "volume_min", None)
        if vmin is not None:
            try:
                volume_min = float(vmin)
            except (TypeError, ValueError):
                pass
        vmax = getattr(symbol_info, "volume_max", None)
        if vmax is not None:
            try:
                volume_max = float(vmax)
            except (TypeError, ValueError):
                pass

    if volume_step > 0:
        remainder = lot_float / volume_step
        steps_rounded = round(remainder)
        if abs(remainder - steps_rounded) > 1e-9:
            return {
                "ok": False,
                "error": "INVALID_LOT_STEP_MISMATCH",
                "reason": f"lot {lot_float} not aligned to step {volume_step}",
            }

    if lot_float < volume_min:
        return {
            "ok": False,
            "error": "INVALID_LOT",
            "reason": f"lot {lot_float} < volume_min {volume_min}",
        }

    if lot_float > volume_max:
        return {
            "ok": False,
            "error": "INVALID_LOT",
            "reason": f"lot {lot_float} > volume_max {volume_max}",
        }

    if risk_percent is not None:
        try:
            risk_float = float(risk_percent)
        except (TypeError, ValueError):
            return {
                "ok": False,
                "error": "INVALID_RISK",
                "reason": "estimated_risk_percent not numeric",
            }
        if not math.isfinite(risk_float):
            return {
                "ok": False,
                "error": "INVALID_RISK",
                "reason": "estimated_risk_percent not finite",
            }
        max_risk = config.get("max_risk_percent", 1.0)
        if risk_float > max_risk:
            return {
                "ok": False,
                "error": "INVALID_RISK",
                "reason": f"risk {risk_float}% > max {max_risk}%",
            }

    return {"ok": True}


def _garantir_memoria():

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if ORDER_MEMORY_FILE.exists():
        return

    with ORDER_MEMORY_FILE.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=ORDER_FIELDS, delimiter=";")
        escritor.writeheader()


def _ler_ordens():

    _garantir_memoria()

    with ORDER_MEMORY_FILE.open("r", encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def _salvar_ordem(registro):

    _garantir_memoria()

    with ORDER_MEMORY_FILE.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=ORDER_FIELDS, delimiter=";")
        escritor.writerow(registro)


def _salvar_ordens(registros):

    _garantir_memoria()

    with ORDER_MEMORY_FILE.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=ORDER_FIELDS, delimiter=";")
        escritor.writeheader()
        escritor.writerows(registros)


def _pre_operacao_ja_executada(pre_operation_id):

    for ordem in _ler_ordens():
        if (
            ordem.get("pre_operation_id") == pre_operation_id
            and ordem.get("status") in ["ENVIADA", "RECUSADA"]
        ):
            return True

    return False


def _ordens_demo_hoje():

    hoje = datetime.now().date().isoformat()
    total = 0

    for ordem in _ler_ordens():
        data = str(ordem.get("data", ""))

        if data.startswith(hoje) and ordem.get("status") == "ENVIADA":
            total += 1

    return total


def _resumo_desempenho_ordens(ativo=None, limite_recente=20):

    hoje = datetime.now().date().isoformat()
    ordens = [
        ordem
        for ordem in _ler_ordens()
        if not ativo or str(ordem.get("ativo", "")).upper() == str(ativo).upper()
    ]
    recentes = ordens[-limite_recente:]

    def contar(registros, status):
        return sum(1 for ordem in registros if ordem.get("status") == status)

    ordens_hoje = [
        ordem
        for ordem in ordens
        if str(ordem.get("data", "")).startswith(hoje)
    ]
    enviadas_recentes = contar(recentes, "ENVIADA")
    recusadas_recentes = contar(recentes, "RECUSADA")
    total_recentes = enviadas_recentes + recusadas_recentes
    taxa_envio = 0

    if total_recentes:
        taxa_envio = round((enviadas_recentes / total_recentes) * 100, 1)

    return {
        "ativo": ativo or "TODOS",
        "hoje_enviadas": contar(ordens_hoje, "ENVIADA"),
        "hoje_recusadas": contar(ordens_hoje, "RECUSADA"),
        "recentes_limite": limite_recente,
        "recentes_enviadas": enviadas_recentes,
        "recentes_recusadas": recusadas_recentes,
        "taxa_envio_recente": taxa_envio,
    }


def _linhas_desempenho_telegram(ativo):

    desempenho = _resumo_desempenho_ordens(ativo=ativo)

    return [
        "Desempenho:",
        (
            f"- Hoje: {desempenho['hoje_enviadas']} enviadas / "
            f"{desempenho['hoje_recusadas']} recusadas"
        ),
        (
            f"- Ultimas {desempenho['recentes_limite']}: "
            f"{desempenho['recentes_enviadas']} enviadas / "
            f"{desempenho['recentes_recusadas']} recusadas"
        ),
        f"- Taxa de envio recente: {desempenho['taxa_envio_recente']}%",
    ]


def _linhas_consciencia_telegram(consciencia):

    if not consciencia:
        return [
            "Consciencia operacional:",
            "- Decisao: SEM DADOS",
            "- Amostras: 0",
        ]

    motivo = str(consciencia.get("reason") or "SEM DADOS")
    if len(motivo) > 160:
        motivo = f"{motivo[:157]}..."

    return [
        "Consciencia operacional:",
        f"- Decisao: {consciencia.get('decision', 'SEM DADOS')}",
        f"- Amostras: {consciencia.get('samples', 0)}",
        f"- Negativas: {consciencia.get('negatives', 0)}",
        f"- Confianca memoria: {consciencia.get('memory_confidence', 0)}",
        f"- Motivo: {motivo}",
    ]


def _linhas_mesa_telegram(mesa):

    if not mesa:
        return [
            "Mesa proprietaria:",
            "- Status: SEM DADOS",
        ]

    if mesa.get("reason") == "FTMO_GUARD_DISABLED":
        return [
            "Mesa proprietaria:",
            "- Status: DESATIVADA",
        ]

    status = "LIBERADA" if mesa.get("approved") else "BLOQUEADA"
    return [
        "Mesa proprietaria:",
        f"- Status: {status}",
        f"- Perda diaria: {mesa.get('daily_loss_percent', 'SEM DADOS')}%",
        f"- Limite interno dia: {mesa.get('daily_buffer_percent', 'SEM DADOS')}%",
        f"- Drawdown: {mesa.get('drawdown_percent', 'SEM DADOS')}%",
        f"- Limite interno drawdown: {mesa.get('drawdown_buffer_percent', 'SEM DADOS')}%",
        f"- Motivo: {mesa.get('reason', 'SEM DADOS')}",
    ]


def _ultima_pre_operacao_aberta():

    if not PRE_OPERATION_FILE.exists():
        return None

    with PRE_OPERATION_FILE.open("r", encoding="utf-8", newline="") as arquivo:
        registros = list(csv.DictReader(arquivo, delimiter=";"))

    candidates = []
    for row in registros:
        if row.get("status") != "ABERTO":
            continue
        validation = validate_setup_evidence(row)
        if not validation.get("ok") or _pre_operacao_ja_executada(row.get("id")):
            continue
        proof = validation.get('proof') or {}
        row['entry_model'] = proof.get('entry_model') or 'UNSPECIFIED'
        row['context_mode'] = ((proof.get('timeframe_details') or {}).get('policy') or {}).get('mode') or 'UNSPECIFIED'
        candidates.append(row)
    for row in candidates:
        row['_selection'] = dict(learning_statistics(row), selected_at=datetime.now().isoformat(), version=VERSION)
    return max(candidates, key=lambda row: (row['_selection']['selection_score'], row.get("data_abertura", ""))) if candidates else None


def liberar_nova_tentativa_mt5(pre_operation_id=None):

    if pre_operation_id is None:
        pre_operacao = _ultima_pre_operacao_aberta()

        if not pre_operacao:
            return _bloqueio("NO_OPEN_PRE_OPERATION_TO_RELEASE")

        pre_operation_id = pre_operacao.get("id")

    ordens = _ler_ordens()
    mantidas = [
        ordem
        for ordem in ordens
        if ordem.get("pre_operation_id") != pre_operation_id
    ]
    removidas = len(ordens) - len(mantidas)

    if removidas == 0:
        return {
            "ok": False,
            "error": "NO_MT5_ATTEMPT_FOUND_FOR_PRE_OPERATION",
            "details": pre_operation_id,
        }

    _salvar_ordens(mantidas)
    registrar_log(
        "MT5 ORDER | nova tentativa liberada para "
        f"{pre_operation_id}; registros removidos: {removidas}"
    )

    return {
        "ok": True,
        "pre_operation_id": pre_operation_id,
        "removed_attempts": removidas,
    }


def _motivo_entrada(pre_operacao):

    return (
        f"Entrada simulada {pre_operacao.get('direcao')} em {pre_operacao.get('ativo')} | "
        f"Setup: {pre_operacao.get('status_setup')} | "
        f"SMC: {pre_operacao.get('smc')} | "
        f"Elliott: {pre_operacao.get('elliott')} | "
        f"BOS: {pre_operacao.get('bos')} | "
        f"CHOCH: {pre_operacao.get('choch')} | "
        f"Confianca: {pre_operacao.get('confianca')} | "
        f"Brain: {pre_operacao.get('brain_score')} | "
        "Execucao protegida em modo teste/demo."
    )


def _bloqueio(error, details=None):

    return {
        "ok": False,
        "error": error,
        "details": details,
    }


def _explicar_retcode(retcode):

    mapa = {
        10027: (
            "AutoTrading desligado no MT5.",
            "Ligue o botão AutoTrading/Algo Trading no MetaTrader 5 e tente novamente.",
        ),
        10018: (
            "Mercado fechado.",
            "Aguarde o mercado abrir para testar nova ordem.",
        ),
        10019: (
            "Saldo ou margem insuficiente.",
            "Reduza lote ou revise margem disponível.",
        ),
        10030: (
            "Tipo de preenchimento não aceito pela corretora.",
            "Será necessário ajustar o modo de envio da ordem.",
        ),
    }

    return mapa.get(
        retcode,
        (
            f"Ordem recusada pelo MT5. Código {retcode}.",
            "Verifique o terminal MT5 antes de nova tentativa.",
        ),
    )


def _resumir_motivo(pre_operacao):

    return [
        f"Setup: {pre_operacao.get('status_setup')}",
        f"Direcao: {pre_operacao.get('direcao')}",
        f"SMC: {pre_operacao.get('smc')}",
        f"Elliott: {pre_operacao.get('elliott')}",
        f"BOS/CHOCH: {pre_operacao.get('bos')} / {pre_operacao.get('choch')}",
        f"Confianca: {pre_operacao.get('confianca')}",
        f"Brain Score: {pre_operacao.get('brain_score')}",
    ]


def _valor(valor, casas=2):

    if valor in [None, ""]:
        return "SEM DADOS"

    try:
        return round(float(valor), casas)
    except (TypeError, ValueError):
        return valor


def _resumo_estudo(pre_operacao):

    return [
        f"Setup: {pre_operacao.get('status_setup', 'SEM DADOS')}",
        f"Classificacao: {pre_operacao.get('classificacao', 'SEM DADOS')}",
        f"SMC: {pre_operacao.get('smc', 'SEM DADOS')}",
        f"Elliott: {pre_operacao.get('elliott', 'SEM DADOS')}",
        f"BOS: {pre_operacao.get('bos', 'SEM DADOS')}",
        f"CHOCH: {pre_operacao.get('choch', 'SEM DADOS')}",
        f"Confianca: {pre_operacao.get('confianca', 'SEM DADOS')}",
        f"Brain Score: {pre_operacao.get('brain_score', 'SEM DADOS')}",
    ]


def _bloco_leon_aprendeu(rr_execucao):

    risco = rr_execucao.get("risk", "SEM DADOS")
    retorno = rr_execucao.get("reward", "SEM DADOS")
    rr_real = rr_execucao.get("rr", "SEM DADOS")

    return [
        "LEON APRENDEU",
        "",
        "A zona tecnica perdeu validade antes da execucao.",
        "O plano foi descartado porque o preco atual nao mantinha o gerenciamento.",
        "",
        "Decisao correta:",
        "- Nao perseguir preco.",
        "- Aguardar nova entrada com risco menor que retorno.",
        "",
        "Resumo do aprendizado:",
        f"- Risco real: {risco}",
        f"- Retorno real: {retorno}",
        f"- RR real: {rr_real}",
        "",
    ]


def _mensagem_bloqueio_preco(
    ativo,
    direcao,
    pre_operacao,
    entrada_planejada,
    preco_atual,
    desvio_entrada,
    limite_desvio,
    rr_execucao,
):

    return "\n".join(
        [
            *_bloco_leon_aprendeu(rr_execucao),
            "LEON | ENTRADA BLOQUEADA PELO GERENCIAMENTO",
            "",
            "Decisao: BLOQUEAR",
            "Motivo: PRECO SAIU DA ZONA PLANEJADA",
            "Modo: estudo/demo protegido",
            "",
            "Plano da entrada:",
            f"- Ativo: {ativo}",
            f"- Direcao: {direcao}",
            f"- Entrada planejada: {_valor(entrada_planejada)}",
            f"- Preco atual: {_valor(preco_atual)}",
            f"- Desvio atual: {_valor(desvio_entrada)}",
            f"- Desvio maximo permitido: {_valor(limite_desvio)}",
            f"- RR planejado: {pre_operacao.get('rr', 'SEM DADOS')}",
            f"- RR real agora: {rr_execucao.get('rr', 'SEM DADOS')}",
            f"- Risco real: {rr_execucao.get('risk', 'SEM DADOS')}",
            f"- Retorno real: {rr_execucao.get('reward', 'SEM DADOS')}",
            "",
            "Leitura SMC + Elliott:",
            *[f"- {linha}" for linha in _resumo_estudo(pre_operacao)],
            "",
            "Explicacao:",
            "- O plano podia fazer sentido na zona original.",
            "- Como o preco andou demais, o RR real ficou ruim.",
            "- O LEON bloqueou para proteger o gerenciamento.",
            "",
            "Melhoria sugerida:",
            "- Aguardar novo retorno para zona valida ou nova pre-operacao.",
        ]
    )


def _mensagem_bloqueio_rr(
    ativo,
    direcao,
    pre_operacao,
    preco_atual,
    stop,
    take_profit,
    min_live_rr,
    rr_execucao,
):

    return "\n".join(
        [
            *_bloco_leon_aprendeu(rr_execucao),
            "LEON | ENTRADA BLOQUEADA PELO GERENCIAMENTO",
            "",
            "Decisao: BLOQUEAR",
            "Motivo: RISCO/RETORNO REAL ABAIXO DO MINIMO",
            "Modo: estudo/demo protegido",
            "",
            "Plano da entrada:",
            f"- Ativo: {ativo}",
            f"- Direcao: {direcao}",
            f"- Preco atual: {_valor(preco_atual)}",
            f"- Stop: {_valor(stop)}",
            f"- Take Profit: {_valor(take_profit)}",
            f"- RR planejado: {pre_operacao.get('rr', 'SEM DADOS')}",
            f"- RR real agora: {rr_execucao.get('rr', 'SEM DADOS')}",
            f"- Piso de protecao: 1:{_valor(min_live_rr)}",
            f"- Risco real: {rr_execucao.get('risk', 'SEM DADOS')}",
            f"- Retorno real: {rr_execucao.get('reward', 'SEM DADOS')}",
            "",
            "Leitura SMC + Elliott:",
            *[f"- {linha}" for linha in _resumo_estudo(pre_operacao)],
            "",
            "Explicacao:",
            "- O gerenciamento nao liberou porque o alvo tecnico nao paga o risco.",
            "- Mesmo em demo, o LEON so deve operar dentro das regras.",
            "",
            "Melhoria sugerida:",
            "- Esperar o preco voltar para a zona e o alvo tecnico pagar ao menos o risco.",
        ]
    )


def _mensagem_ordem_demo_enviada(
    ativo,
    direcao,
    pre_operacao,
    lote,
    plano_risco,
    preco_entrada,
    stop,
    take_profit,
    rr_execucao,
    ticket,
    consciencia=None,
    mesa=None,
):

    return "\n".join(
        [
            "LEON | ORDEM DEMO ENVIADA",
            "",
            "Decisao: ENTRAR EM DEMO",
            "Modo: estudo/demo protegido",
            "",
            "Execucao:",
            f"- Ativo: {ativo}",
            f"- Direcao: {direcao}",
            f"- Lote calculado: {lote}",
            f"- Entrada real: {_valor(preco_entrada)}",
            f"- Stop: {_valor(stop)}",
            f"- Take Profit: {_valor(take_profit)}",
            f"- RR real: {rr_execucao.get('rr', 'SEM DADOS')}",
            f"- Ticket: {ticket}",
            "",
            "Gerenciamento:",
            f"- Risco estimado: {plano_risco['estimated_risk']}",
            f"- Risco em %: {plano_risco['estimated_risk_percent']}%",
            f"- Risco real: {rr_execucao.get('risk', 'SEM DADOS')}",
            f"- Retorno real: {rr_execucao.get('reward', 'SEM DADOS')}",
            "",
            *_linhas_desempenho_telegram(ativo),
            "",
            *_linhas_mesa_telegram(mesa),
            "",
            *_linhas_consciencia_telegram(consciencia),
            "",
            "Leitura SMC + Elliott:",
            *[f"- {linha}" for linha in _resumo_estudo(pre_operacao)],
            "",
            "Motivo:",
            "- Entrada liberada porque passou no gerenciamento atual.",
            "- O print do MT5 sera enviado em seguida quando disponivel.",
        ]
    )


def _registrar_aprendizado_gerenciamento(motivo, rr_execucao, observacao_extra=""):

    rr_real = rr_execucao.get("rr", "SEM DADOS")
    risco = rr_execucao.get("risk", "SEM DADOS")
    retorno = rr_execucao.get("reward", "SEM DADOS")
    observacao = (
        f"{motivo}. Stop tecnico preservado. "
        f"Risco real: {risco}. Retorno real: {retorno}. RR real: {rr_real}. "
        "O LEON deve aguardar novo preco que pague o risco, sem perseguir entrada."
    )

    if observacao_extra:
        observacao = f"{observacao} {observacao_extra}"

    try:
        registrar_contexto_cerebro(
            origem="risk_manager",
            tipo="plano_invalidado_gerenciamento",
            observacao=observacao,
        )
    except Exception as erro:
        registrar_erro(f"MT5 ORDER | falha ao registrar aprendizado: {erro}")


def _rr_no_preco_execucao(direcao, preco_execucao, stop, take_profit):

    risco = abs(preco_execucao - stop)
    recompensa = abs(take_profit - preco_execucao)

    if risco <= 0:
        return {
            "approved": False,
            "error": "INVALID_LIVE_RISK_DISTANCE",
            "risk": round(risco, 2),
            "reward": round(recompensa, 2),
            "rr": 0,
        }

    if direcao == "COMPRA" and not (stop < preco_execucao < take_profit):
        return {
            "approved": False,
            "error": "INVALID_BUY_PRICE_STRUCTURE",
            "risk": round(risco, 2),
            "reward": round(recompensa, 2),
            "rr": round(recompensa / risco, 2),
        }

    if direcao == "VENDA" and not (take_profit < preco_execucao < stop):
        return {
            "approved": False,
            "error": "INVALID_SELL_PRICE_STRUCTURE",
            "risk": round(risco, 2),
            "reward": round(recompensa, 2),
            "rr": round(recompensa / risco, 2),
        }

    return {
        "approved": True,
        "risk": round(risco, 2),
        "reward": round(recompensa, 2),
        "rr": round(recompensa / risco, 2),
    }


def executar_ordem_mt5_pre_operacao(forcar=False):

    config = _execution_config()
    risk_gate = _risk_gate_config()

    if not config["enabled"]:
        return _bloqueio("MT5_EXECUTION_DISABLED")

    autonomia = status_autonomia()
    if (
        not autonomia.get("active")
        or autonomia.get("scope") not in {"demo_execution", "learning_and_demo"}
    ):
        return _bloqueio("AUTONOMY_SCOPE_BLOCKED", autonomia)

    limite_diario = avaliar_limite_perda_diaria()
    if not limite_diario.get("ok"):
        return _bloqueio("DAILY_LOSS_GUARD_UNAVAILABLE", limite_diario)
    if not limite_diario.get("approved"):
        registrar_log(
            f"MT5 ORDER | bloqueada por perda diaria: {limite_diario}"
        )
        return _bloqueio("DAILY_LOSS_LIMIT_REACHED", limite_diario)

    # ── FTMO Guard (kill switch automatico, adicional) ────────────────────
    # Ativo apenas quando [FTMO] enabled=true. Detecta a conta ao vivo,
    # ancora baseline por login e aplica buffer interno (mais conservador
    # que os limites FTMO). NAO substitui os guards acima; nao envia ordem.
    ftmo = avaliar_guard_ftmo()
    if not ftmo.get("reason") == "FTMO_GUARD_DISABLED":
        if not ftmo.get("ok"):
            registrar_log(f"MT5 ORDER | FTMO guard indisponivel: {ftmo}")
            return _bloqueio("FTMO_GUARD_UNAVAILABLE", ftmo)
        if not ftmo.get("approved"):
            registrar_log(f"MT5 ORDER | bloqueada pelo FTMO guard: {ftmo}")
            return _bloqueio("FTMO_LIMIT_REACHED", ftmo)

    pre_operacao = _ultima_pre_operacao_aberta()

    if not pre_operacao:
        return _bloqueio("NO_OPEN_PRE_OPERATION_TO_EXECUTE")

    pre_operation_id = pre_operacao.get("id")

    structural_gate = validate_setup_evidence(pre_operacao)
    if not structural_gate.get("ok"):
        return _bloqueio(structural_gate.get("error", "STRUCTURAL_GATE_FAILED"), structural_gate)

    # ── Modo LAB_LEARNING ────────────────────────────────────────────────
    # Pre-ops com zona de laboratorio (zone_source=LABORATORIO) relaxam
    # apenas o timeframe_policy (top-down) para aprendizado em demo com
    # risco minimo (lote 0.01). Corrigido em 2026-08-18 (pendencia #10):
    # o SMC guard NAO e pulado — permanece sempre ativo em qualquer rota.
    # Todos os guards de SEGURANCA permanecem ativos (conta real, daily
    # loss, noticias, conselho, limite diario, spread maximo).
    lab_learning_mode = False
    if lab_learning_mode:
        registrar_log(
            f"MT5 ORDER | LAB_LEARNING: pre-op {pre_operation_id} "
            "usando zona de laboratorio — SMC guard sempre ativo, "
            "timeframe_policy relaxado pelo laboratorio."
        )

    # ── News Shield (sempre ativo) ───────────────────────────────────────
    news_shield = avaliar_news_shield()
    if not news_shield.get("approved") and lab_learning_mode:
        registrar_log(
            f"MT5 ORDER | LAB_LEARNING: news shield em aviso, sem bloqueio: "
            f"{news_shield}"
        )
    elif not news_shield.get("approved"):
        registrar_relatorio_operacao(
            pre_operacao,
            decisao="BLOQUEAR",
            motivo="HIGH_IMPACT_NEWS_WINDOW",
        )
        return _bloqueio("HIGH_IMPACT_NEWS_WINDOW", news_shield)

    # ── Estudo Operacional (score) ────────────────────────────────────
    _liq_ev = pre_operacao.get("liquidity")
    if not isinstance(_liq_ev, dict):
        _liq_ev = {}
    ctx_estudo = {
        "direction": "COMPRA" if pre_operacao.get("direcao") == "COMPRA" else "VENDA",
        "trend": None,
        "momentum": None,
        "liquidity_event": _liq_ev.get("type"),
        "bos": pre_operacao.get("bos"),
        "choch": pre_operacao.get("choch"),
        "fvg": pre_operacao.get("fvg"),
        "poi_score": pre_operacao.get("brain_score", 0),
        "top_down": None,
        "session": None,
        "rr": pre_operacao.get("rr", 0),
        "high_impact_news": False,
        "market_state": None,
    }
    score_estudo = score_operational_context(ctx_estudo)
    min_score_estudo = config["lab_min_setup_score"] if lab_learning_mode else 70
    if score_estudo < min_score_estudo and lab_learning_mode:
        registrar_log(
            f"MT5 ORDER | LAB_LEARNING: score baixo vira aprendizado "
            f"pre-op {pre_operation_id}: "
            f"score={score_estudo} < {min_score_estudo}"
        )
    elif score_estudo < min_score_estudo and not structural_gate.get("ok"):
        registrar_log(
            f"MT5 ORDER | score operacional baixo "
            f"pre-op {pre_operation_id}: "
            f"score={score_estudo} < {min_score_estudo}"
        )
        registrar_relatorio_operacao(
            pre_operacao,
            decisao="BLOQUEAR",
            motivo="SCORE_OPERACIONAL_BAIXO",
        )
        return _bloqueio(
            "SCORE_OPERACIONAL_BAIXO",
            {
                "score": score_estudo,
                "min_score": min_score_estudo,
            },
        )
    registrar_log(
        f"MT5 ORDER | score operacional ok "
        f"pre-op {pre_operation_id}: score={score_estudo}"
    )

    # ── SMC Guard ────────────────────────────────────────────────────────
    # Sempre ativo — inclusive em modo LAB_LEARNING (correção 2026-08-18,
    # pendência #10). A zona de laboratorio NÃO substitui a confirmacao SMC;
    # comprar topo / vender fundo permanece bloqueado em qualquer rota.
    smc_guard = validate_smc_entry(
        pre_operacao.get("direcao"),
        pre_operacao.get("smc"),
        pre_operacao.get("bos"),
        pre_operacao.get("choch"),
        region_id=pre_operacao.get('region_id',''),
        pre_operation_id=pre_operacao.get('id'),
        symbol=pre_operacao.get('ativo'),
    )
    if not smc_guard["approved"] and lab_learning_mode:
        registrar_log(
            f"MT5 ORDER | LAB_LEARNING: SMC divergente vira aprendizado "
            f"pre-op {pre_operation_id}: {smc_guard}"
        )
    elif not smc_guard["approved"]:
        registrar_relatorio_operacao(
            pre_operacao,
            decisao="BLOQUEAR",
            motivo="SMC_STRUCTURE_NOT_CONFIRMED",
        )
        return _bloqueio("SMC_STRUCTURE_NOT_CONFIRMED", smc_guard)

    sessao = identificar_sessao()
    if sessao == "MANUTENCAO" and lab_learning_mode:
        registrar_log(
            f"MT5 ORDER | LAB_LEARNING: sessao em manutencao registrada "
            f"como aviso para pre-op {pre_operation_id}"
        )
    elif sessao == "MANUTENCAO":
        registrar_relatorio_operacao(
            pre_operacao,
            decisao="BLOQUEAR",
            motivo="MAINTENANCE_BREAK",
        )
        return _bloqueio("MAINTENANCE_BREAK", sessao)

    # ── Timeframe Policy (Top-Down) ──────────────────────────────────────
    # Pulado em modo LAB_LEARNING — o laboratorio nao exige alinhamento
    # top-down completo para operacoes de aprendizado em demo.
    top_down = ultima_leitura_top_down()
    if lab_learning_mode:
        registrar_log(
            f"MT5 ORDER | LAB_LEARNING: timeframe_policy skipped para "
            f"pre-op {pre_operation_id} (zona de laboratorio)"
        )
        # Cria um timeframe_policy ficticio apenas para log/rrastro
        timeframe_policy = {
            "approved": True,
            "mode": "LAB_LEARNING",
            "risk_factor": 0.5,
            "reason": "LABORATORIO: aprendizado em demo sem alinhamento top-down",
        }
    else:
        timeframe_policy = evaluate_daytrade_context(
            top_down,
            pre_operacao.get("direcao"),
        )
        if not timeframe_policy["approved"]:
            detalhes = {
                "direction": pre_operacao.get("direcao"),
                "alignment": top_down.get("alinhamento"),
                "m15_trigger": top_down.get("m15_gatilho"),
                "policy": timeframe_policy,
            }
            registrar_relatorio_operacao(
                pre_operacao,
                decisao="BLOQUEAR",
                motivo="TOP_DOWN_M15_NOT_ALIGNED",
            )
            return _bloqueio("TOP_DOWN_M15_NOT_ALIGNED", detalhes)

    try:
        brain_score = float(pre_operacao.get("brain_score") or 0)
    except ValueError:
        brain_score = 0

    laboratorio = False
    min_score = (
        config["lab_min_setup_score"]
        if laboratorio
        else risk_gate["min_setup_score"]
    )
    min_live_rr = (
        config["lab_min_live_rr"]
        if laboratorio
        else config["min_live_rr"]
    )
    max_entry_drift = (
        config["lab_max_entry_drift_points"]
        if laboratorio
        else config["max_entry_drift_points"]
    )

    if brain_score < min_score and lab_learning_mode:
        registrar_log(
            f"MT5 ORDER | LAB_LEARNING: brain score baixo vira aprendizado "
            f"pre-op {pre_operation_id}: {brain_score} < {min_score}"
        )
    elif brain_score < min_score and not structural_gate.get("ok"):
        registrar_relatorio_operacao(
            pre_operacao,
            decisao="BLOQUEAR",
            motivo="SETUP_SCORE_BELOW_MINIMUM",
        )
        return _bloqueio(
            "SETUP_SCORE_BELOW_MINIMUM",
            {
                "brain_score": brain_score,
                "min_setup_score": min_score,
                "demo_only": config["demo_only"],
                "pre_operation_id": pre_operation_id,
            },
        )

    if _pre_operacao_ja_executada(pre_operation_id):
        return _bloqueio("MT5_ORDER_ALREADY_SENT_FOR_PRE_OPERATION", pre_operation_id)

    ordens_hoje = _ordens_demo_hoje()

    if (
        config["max_demo_orders_day"] > 0
        and ordens_hoje >= config["max_demo_orders_day"]
    ):
        return _bloqueio(
            "MAX_DEMO_ORDERS_DAY_REACHED",
            {
                "orders_today": ordens_hoje,
                "limit": config["max_demo_orders_day"],
            },
        )

    conselho = avaliar_conselho_operadores()

    if lab_learning_mode and conselho["decision"] == "BLOQUEADO":
        registrar_log(
            f"MT5 ORDER | LAB_LEARNING: conselho bloqueou mas modo "
            f"laboratorio ignora: {conselho['summary']}"
        )
    elif conselho["decision"] == "BLOQUEADO" and not structural_gate.get("ok"):
        return _bloqueio("OPERATOR_COUNCIL_BLOCKED", conselho)

    mt5_inicializado = False

    try:
        import mt5_safe as mt5

        if not mt5.initialize():
            return _bloqueio("MT5_INITIALIZE_FAILED", str(mt5.last_error()))
        mt5_inicializado = True

        account = mt5.account_info()

        if account is None:
            mt5.shutdown()
            return _bloqueio("MT5_ACCOUNT_NOT_AVAILABLE")

        if config["demo_only"] and account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            mt5.shutdown()
            return _bloqueio(
                "MT5_REAL_ACCOUNT_BLOCKED",
                "Executor configurado para demo_only.",
            )

        if config["max_open_positions"] > 0:
            positions = mt5.positions_get()
            if positions is not None and len(positions) >= config["max_open_positions"]:
                mt5.shutdown()
                registrar_log(
                    f"MT5 ORDER | MAX_OPEN_POSITIONS_REACHED: "
                    f"{len(positions)} abertas, limite {config['max_open_positions']}"
                )
                return _bloqueio(
                    "MAX_OPEN_POSITIONS_REACHED",
                    {
                        "open_positions": len(positions),
                        "limit": config["max_open_positions"],
                    },
                )

        ativo = pre_operacao["ativo"]
        direcao = pre_operacao["direcao"]
        saldo_conta = float(account.balance)

        mt5.symbol_select(ativo, True)
        tick = mt5.symbol_info_tick(ativo)

        if tick is None:
            mt5.shutdown()
            return _bloqueio("MT5_TICK_NOT_AVAILABLE", ativo)

        symbol_info = mt5.symbol_info(ativo)

        if symbol_info is None:
            mt5.shutdown()
            return _bloqueio("MT5_SYMBOL_INFO_NOT_AVAILABLE", ativo)

        spread = abs(tick.ask - tick.bid)

        if spread > config["max_spread"]:
            mt5.shutdown()
            return _bloqueio("SPREAD_ABOVE_LIMIT", spread)

        if direcao == "COMPRA":
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
            tp = float(pre_operacao["tp2"])

        elif direcao == "VENDA":
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
            tp = float(pre_operacao["tp2"])

        else:
            mt5.shutdown()
            return _bloqueio("INVALID_ORDER_DIRECTION", direcao)

        sl = float(pre_operacao["stop"])
        entrada_planejada = float(pre_operacao["entrada"])
        desvio_entrada = abs(price - entrada_planejada)
        rr_execucao = _rr_no_preco_execucao(direcao, price, sl, tp)

        if desvio_entrada > max_entry_drift:
            mt5.shutdown()
            detalhes = {
                "planned_entry": entrada_planejada,
                "execution_price": round(price, 2),
                "drift": round(desvio_entrada, 2),
                "max_entry_drift_points": max_entry_drift,
                "learning_lab": laboratorio,
                "live_rr": rr_execucao,
            }
            registrar_log(f"MT5 ORDER | bloqueada por desvio de entrada: {detalhes}")
            registrar_relatorio_operacao(
                pre_operacao,
                decisao="BLOQUEAR",
                motivo="ENTRY_PRICE_DRIFT_ABOVE_LIMIT",
                preco_real=price,
                rr_real=rr_execucao.get("rr"),
            )
            invalidacao = invalidar_pre_operacao(
                pre_operation_id,
                "INVALIDADA_GERENCIAMENTO",
                (
                    "Plano invalidado: preco saiu da zona planejada. "
                    f"Desvio {round(desvio_entrada, 2)} acima do limite "
                    f"{max_entry_drift}."
                ),
            )
            registrar_log(f"PRE-OPERACAO | invalidacao por desvio: {invalidacao}")
            _registrar_aprendizado_gerenciamento(
                "Plano invalidado porque o preco saiu da zona SMC planejada",
                rr_execucao,
                f"Desvio: {round(desvio_entrada, 2)}.",
            )
            enviar_mensagem(
                _mensagem_bloqueio_preco(
                    ativo=ativo,
                    direcao=direcao,
                    pre_operacao=pre_operacao,
                    entrada_planejada=entrada_planejada,
                    preco_atual=price,
                    desvio_entrada=desvio_entrada,
                    limite_desvio=max_entry_drift,
                    rr_execucao=rr_execucao,
                )
            )
            return _bloqueio("ENTRY_PRICE_DRIFT_ABOVE_LIMIT", detalhes)

        if (
            not rr_execucao.get("approved")
            or rr_execucao["rr"] < min_live_rr
        ):
            mt5.shutdown()
            detalhes = {
                "min_live_rr": min_live_rr,
                "learning_lab": laboratorio,
                "planned_rr": pre_operacao.get("rr"),
                "live_rr": rr_execucao,
                "execution_price": round(price, 2),
                "stop": sl,
                "take_profit": tp,
            }
            registrar_log(f"MT5 ORDER | bloqueada por RR real invalido: {detalhes}")
            registrar_relatorio_operacao(
                pre_operacao,
                decisao="BLOQUEAR",
                motivo="LIVE_RR_BELOW_MINIMUM",
                preco_real=price,
                rr_real=rr_execucao.get("rr"),
            )
            invalidacao = invalidar_pre_operacao(
                pre_operation_id,
                "INVALIDADA_GERENCIAMENTO",
                (
                    "Plano invalidado: RR real ficou abaixo do minimo. "
                    f"RR real {rr_execucao.get('rr')} menor que "
                    f"{min_live_rr}."
                ),
            )
            registrar_log(f"PRE-OPERACAO | invalidacao por RR: {invalidacao}")
            _registrar_aprendizado_gerenciamento(
                "Plano invalidado porque o RR real ficou menor que o minimo",
                rr_execucao,
                f"RR minimo: {min_live_rr}.",
            )
            enviar_mensagem(
                _mensagem_bloqueio_rr(
                    ativo=ativo,
                    direcao=direcao,
                    pre_operacao=pre_operacao,
                    preco_atual=price,
                    stop=sl,
                    take_profit=tp,
                    min_live_rr=min_live_rr,
                    rr_execucao=rr_execucao,
                )
            )
            return _bloqueio("LIVE_RR_BELOW_MINIMUM", detalhes)

        pre_operacao_execucao = dict(pre_operacao)
        pre_operacao_execucao["entrada"] = price
        pre_operacao_execucao["context_mode"] = timeframe_policy["mode"]

        especificacoes = {
            "contract_size": float(
                getattr(symbol_info, "trade_contract_size", 0) or 0
            ),
            "volume_step": float(
                getattr(symbol_info, "volume_step", 0) or 0
            ),
            "volume_min": float(
                getattr(symbol_info, "volume_min", 0) or 0
            ),
            "volume_max": float(
                getattr(symbol_info, "volume_max", 0) or 0
            ),
            "tick_size": float(
                getattr(symbol_info, "trade_tick_size", 0) or 0
            ),
            "tick_value": float(
                getattr(symbol_info, "trade_tick_value", 0) or 0
            ),
            "symbol_logic": ativo,
            "symbol_resolved": ativo,
            "account_currency": getattr(
                getattr(account, "currency", None), "currency", ""
            ),
            "calculation_mode": getattr(
                symbol_info, "trade_calc_mode", ""
            ),
        }

        plano_risco = calcular_plano_risco(
            pre_operacao_execucao,
            saldo=saldo_conta,
            especificacoes=especificacoes,
        )

        if not plano_risco.get("approved"):
            mt5.shutdown()
            registrar_relatorio_operacao(
                pre_operacao,
                decisao="BLOQUEAR",
                motivo="RISK_CONTROL_BLOCKED",
                preco_real=price,
                rr_real=rr_execucao.get("rr"),
            )
            return _bloqueio("RISK_CONTROL_BLOCKED", plano_risco)

        orcamento_risco = avaliar_orcamento_risco_aberto(
            plano_risco["estimated_risk_percent"]
        )
        if not orcamento_risco.get("approved"):
            registrar_relatorio_operacao(
                pre_operacao,
                decisao="BLOQUEAR",
                motivo="OPEN_RISK_BUDGET_EXCEEDED",
                preco_real=price,
                rr_real=rr_execucao.get("rr"),
            )
            return _bloqueio(
                "OPEN_RISK_BUDGET_EXCEEDED",
                orcamento_risco,
            )

        consciencia = avaliar_consciencia_operacional(pre_operacao_execucao)
        if lab_learning_mode and not consciencia.get("approved", True):
            consciencia = dict(consciencia)
            consciencia["approved"] = True
            consciencia["decision"] = "REDUZIR_RISCO"
            consciencia["risk_factor"] = min(
                float(consciencia.get("risk_factor") or 1.0),
                0.5,
            )
            consciencia["lab_override"] = True
            consciencia["reason"] = (
                "Laboratorio demo liberado para aprender executando; "
                "memoria ruim reduz risco em vez de bloquear."
            )
        registrar_log(
            "MT5 ORDER | consciencia operacional: "
            f"decisao={consciencia.get('decision')} "
            f"amostras={consciencia.get('samples')} "
            f"negativas={consciencia.get('negatives')} "
            f"confianca={consciencia.get('memory_confidence')}"
        )
        if not consciencia.get("approved", True):
            mt5.shutdown()
            registrar_relatorio_operacao(
                pre_operacao,
                decisao="BLOQUEAR",
                motivo="MEMORY_CONSCIOUSNESS_BLOCKED",
                preco_real=price,
                rr_real=rr_execucao.get("rr"),
            )
            return _bloqueio("MEMORY_CONSCIOUSNESS_BLOCKED", consciencia)

        lote = plano_risco["lot"]
        fator_memoria = float(consciencia.get("risk_factor") or 1.0)
        if 0 < fator_memoria < 1 and not config.get("percentage_sizing"):
            lote_original = lote
            lote = round(max(0.01, lote * fator_memoria), 2)
            plano_risco = dict(plano_risco)
            plano_risco["lot"] = lote
            plano_risco["memory_original_lot"] = lote_original
            plano_risco["memory_risk_factor"] = fator_memoria
            registrar_log(
                f"MT5 ORDER | consciencia reduziu lote "
                f"{lote_original} -> {lote}"
            )

        validacao_lote = _validar_lote_executor(plano_risco, config, symbol_info)
        if not validacao_lote.get("ok"):
            mt5.shutdown()
            return _bloqueio(
                validacao_lote["error"],
                {
                    "lot": lote,
                    "reason": validacao_lote.get("reason"),
                    "risk_plan": plano_risco,
                },
            )

        if not config.get("percentage_sizing") and lote > config["lot"]:
            if lab_learning_mode:
                lote = config["lot"]
                registrar_log(
                    f"MT5 ORDER | LAB_LEARNING: lote acima do limite; "
                    f"cap para {lote}"
                )
            else:
                mt5.shutdown()
                return _bloqueio(
                    "LOT_ABOVE_EXECUTION_LIMIT",
                    {
                        "lot": lote,
                        "execution_limit": config["lot"],
                        "risk_plan": plano_risco,
                    },
                )
        motivo = _motivo_entrada(pre_operacao)
        motivo = (
            f"{motivo} | CONSCIENCIA: {consciencia.get('decision')} - "
            f"{consciencia.get('reason')}"
        )
        if laboratorio:
            motivo = (
                f"{motivo} | APRENDIZADO OPERACIONAL DEMO: experiencia real "
                f"com score minimo {min_score}, RR minimo {min_live_rr} "
                f"e desvio maximo {max_entry_drift}. "
                f"Contexto {timeframe_policy['mode']}."
            )

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": ativo,
            "volume": lote,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": config["deviation"],
            "magic": config["magic"],
            "comment": "LEON_PREOP_TEST",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # SAFETY: order_send is called ONLY after all guards passed:
        #   - demo_only check, daily loss, SMC structure, news shield,
        #   - top-down alignment, brain score, operator council,
        #   - spread limit, entry drift, live RR, risk control, lot validation.
        # Dynamically resolve mt5linux_compat to support test mocking.
        # Using direct import (not mt5_safe) because mt5_safe blocks order_send.
        import mt5linux_compat as _mt5_exec  # noqa: E402
        final_gate = validate_setup_evidence(pre_operacao)
        if not final_gate.get('ok'):
            return _bloqueio(final_gate.get('error', 'STRUCTURAL_GATE_FAILED'), final_gate)
        resultado = _mt5_exec.order_send(request)
        if resultado is None:
            err_code, err_desc = _mt5_exec.last_error()
            registrar_log(
                f"MT5 ORDER | order_send retornou None: "
                f"{err_code} {err_desc}; reconectando..."
            )
            _mt5_exec.shutdown()
            if _mt5_exec.initialize():
                final_gate = validate_setup_evidence(pre_operacao)
                if not final_gate.get('ok'):
                    return _bloqueio(final_gate.get('error', 'STRUCTURAL_GATE_FAILED'), final_gate)
                resultado = _mt5_exec.order_send(request)
                if resultado is not None:
                    registrar_log(
                        "MT5 ORDER | order_send reenviado "
                        "apos reconexao"
                    )
            if resultado is None:
                mt5.shutdown()
                mt5_inicializado = False
                return _bloqueio(
                    "MT5_ORDER_SEND_FAILED",
                    _mt5_exec.last_error(),
                )
        mt5.shutdown()
        mt5_inicializado = False
        retcode = getattr(resultado, "retcode", None)
        ticket = getattr(resultado, "order", None)
        ok = retcode == mt5.TRADE_RETCODE_DONE

        registro = {
            "data": datetime.now().isoformat(timespec="seconds"),
            "pre_operation_id": pre_operation_id,
            "ativo": ativo,
            "direcao": direcao,
            "lote": lote,
            "entrada": price,
            "stop": sl,
            "tp": tp,
            "status": "ENVIADA" if ok else "RECUSADA",
            "retcode": retcode,
            "ticket": ticket,
            "motivo": motivo,
        }
        _salvar_ordem(registro)

        if ok:
            atomic_json(DATA_DIR / "order_evidence" / f"{account.server}-{account.login}-{ticket}.json", {
                "account_key": f"{account.server}:{account.login}", "order_ticket": ticket,
                "pre_operation_id": pre_operation_id, "setup_version": VERSION,
                "entry_model": pre_operacao.get('entry_model', 'UNSPECIFIED'),
                "context_mode": pre_operacao.get('context_mode', 'UNSPECIFIED'),
                "initial_risk": plano_risco["estimated_risk"],
                "selection_score": pre_operacao.get('_selection', {}).get('selection_score'),
                "selection_statistics": pre_operacao.get('_selection', {}),
            })
            registrar_log(f"MT5 ORDER | ordem teste enviada: {registro}")
            registrar_relatorio_operacao(
                pre_operacao,
                decisao="ENTRAR",
                motivo="ORDEM_TESTE_ENVIADA",
                preco_real=price,
                rr_real=rr_execucao.get("rr"),
            )
            enviar_mensagem(
                _mensagem_ordem_demo_enviada(
                    ativo=ativo,
                    direcao=direcao,
                    pre_operacao=pre_operacao,
                    lote=lote,
                    plano_risco=plano_risco,
                    preco_entrada=price,
                    stop=sl,
                    take_profit=tp,
                    rr_execucao=rr_execucao,
                    ticket=ticket,
                    consciencia=consciencia,
                    mesa=ftmo,
                )
            )
            snapshot = capturar_print_mt5(
                pre_operation_id=pre_operation_id,
                ativo=ativo,
            )

            if not snapshot.get("ok"):
                registrar_log(f"MT5 ORDER | print MT5 nao gerado: {snapshot}")
                snapshot = gerar_print_entrada(
                    ativo=ativo,
                    direcao=direcao,
                    entrada=price,
                    stop=sl,
                    take_profit=tp,
                    pre_operation_id=pre_operation_id,
                )

            if snapshot.get("ok"):
                resultado_foto = enviar_foto(
                    snapshot["path"],
                    (
                        "LEON | PRINT DA ENTRADA MT5\n"
                        f"{snapshot.get('caption')}\n"
                        f"Pre-op: {pre_operation_id}\n"
                        "Imagem capturada do MetaTrader 5 quando disponivel."
                    ),
                )
                message_id = (
                    resultado_foto.get("result", {}).get("message_id")
                    if isinstance(resultado_foto, dict)
                    else None
                )
                registrar_log(
                    "MT5 ORDER | print Telegram concluido: "
                    f"ok={resultado_foto.get('ok', False)} "
                    f"message_id={message_id}"
                )
            else:
                registrar_log(f"MT5 ORDER | print nao gerado: {snapshot}")
        else:
            registrar_log(f"MT5 ORDER | ordem recusada: {registro}")
            registrar_relatorio_operacao(
                pre_operacao,
                decisao="BLOQUEAR",
                motivo=f"MT5_RETCODE_{retcode}",
                preco_real=price,
                rr_real=rr_execucao.get("rr"),
            )
            explicacao, acao = _explicar_retcode(retcode)
            enviar_mensagem(
                "\n".join(
                    [
                        "LEON | ORDEM TESTE NAO EXECUTADA",
                        "",
                        f"Ativo: {ativo}",
                        f"Direcao: {direcao}",
                        f"Lote: {lote}",
                        f"Risco: {plano_risco['estimated_risk']} ({plano_risco['estimated_risk_percent']}%)",
                        f"Entrada: {price}",
                        f"Stop: {sl}",
                        f"Alvo: {tp}",
                        "",
                        "Status:",
                        explicacao,
                        "",
                        "Acao recomendada:",
                        acao,
                        "",
                        "Motivo da entrada:",
                        *_resumir_motivo(pre_operacao),
                    ]
                )
            )

        return {
            "ok": ok,
            "order": registro,
            "raw": str(resultado),
            "memory_consciousness": consciencia,
        }

    except Exception as erro:
        registrar_erro(f"MT5 ORDER | falha no executor: {erro}")
        enviar_erro_sistema(erro, contexto="executor MT5")
        return _bloqueio("MT5_ORDER_EXCEPTION", str(erro))
    finally:
        if mt5_inicializado:
            try:
                mt5.shutdown()
            except Exception as erro_shutdown:
                registrar_erro(
                    f"MT5 ORDER | falha ao encerrar conexao MT5: {erro_shutdown}"
                )
