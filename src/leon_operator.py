# ===================================
# PROFESSOR LEON OPERATOR
# ===================================

import argparse
import configparser
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import date, datetime
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.autonomy_guard import (
    conceder_autonomia,
    revogar_autonomia,
    status_autonomia,
)
from src.brain_context_memory import registrar_contexto_cerebro
from src.brain_memory import registrar_brain
from src.collector_operator import executar_coleta_manual
from src.daily_learning_report import gerar_relatorio_aprendizado_diario
from src.daily_operator_report import gerar_relatorio_operador_diario
from src.emotion_engine import register_emotional_event
from src.error_logger import registrar_erro
from src.log_engine import registrar_log
from src.mt5_order_executor import (
    executar_ordem_mt5_pre_operacao,
    liberar_nova_tentativa_mt5,
)
from src.market_context_agent import registrar_contexto_mercado
from src.market_session_guard import (
    inspect_broker_session,
    maintenance_is_due,
    mark_maintenance_done,
    register_session_status,
    restart_mt5_connection,
)
from src.pre_operation_engine import avaliar_pre_operacoes_abertas
from src.pre_operation_engine import resumo_pre_operacao
from src.performance_tracker import registrar_performance
from src.setup_audit import generate_setup_audit
from src.operation_report import registrar_relatorio_operacao
from src.operation_close_alert import send_operation_close_alert
from src.operation_batch_review import process_operation_batches
from src.mt5_operation_close_monitor import check_mt5_closed_operations
from src.telegram_alert import (
    enviar_alerta_conflito_operadores,
    enviar_alerta_dados_antigos,
    enviar_alerta_operador_encerrado,
    enviar_erro_sistema,
    enviar_relatorio_aprendizado_texto,
    enviar_revisao_operacoes_texto,
    enviar_status_operadores,
)


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "config.ini"
DATA_DIR = ROOT_DIR / "data"
STATE_FILE = DATA_DIR / "daily_learning_state.txt"
STATUS_STATE_FILE = DATA_DIR / "telegram_status_state.txt"
CONFLICT_STATE_FILE = DATA_DIR / "alignment_conflict_state.txt"
STALE_DATA_STATE_FILE = DATA_DIR / "stale_data_state.txt"
COLLECTOR_STATE_FILE = DATA_DIR / "collector_state.txt"
ANALYSIS_STATE_FILE = DATA_DIR / "analysis_state.txt"
DEMO_EXECUTION_STATE_FILE = DATA_DIR / "demo_execution_state.txt"
OPERATOR_HEARTBEAT_FILE = DATA_DIR / "operator_heartbeat.json"


def _ler_inteiro_config(secao, chave, padrao, minimo=1):

    try:
        valor = secao.getint(chave, fallback=padrao)
    except (TypeError, ValueError):
        registrar_erro(
            f"OPERATOR | configuracao invalida: {chave}; usando {padrao}"
        )
        return padrao

    if valor < minimo:
        registrar_erro(
            f"OPERATOR | configuracao fora do limite: {chave}={valor}; "
            f"usando {padrao}"
        )
        return padrao

    return valor


def _normalizar_horario(valor, padrao="23:55"):

    try:
        datetime.strptime(valor, "%H:%M")
    except (TypeError, ValueError):
        registrar_erro(
            f"OPERATOR | horario invalido: {valor!r}; usando {padrao}"
        )
        return padrao

    return valor


def _escrever_texto_atomico(caminho, conteudo):

    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(
        f".{caminho.name}.{os.getpid()}.tmp"
    )

    try:
        temporario.write_text(conteudo, encoding="utf-8")
        temporario.replace(caminho)
    finally:
        try:
            temporario.unlink(missing_ok=True)
        except OSError:
            pass


def _ler_texto_estado(caminho):

    if not caminho.exists():
        return ""

    try:
        return caminho.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as erro:
        registrar_erro(
            f"OPERATOR | falha ao ler estado {caminho.name}: {erro}"
        )
        return ""


def _registrar_heartbeat(estado, detalhes=None):

    payload = {
        "status": estado,
        "pid": os.getpid(),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    if detalhes:
        payload["details"] = detalhes

    try:
        _escrever_texto_atomico(
            OPERATOR_HEARTBEAT_FILE,
            json.dumps(payload, indent=2, ensure_ascii=True),
        )
    except OSError as erro:
        registrar_erro(f"OPERATOR | falha ao gravar heartbeat: {erro}")


def _iniciar_identidade_ciclo():
    from datetime import timezone
    ciclo = f"CYCLE-{int(datetime.now(timezone.utc).timestamp())}"
    analise = f"ANALYSIS-{int(datetime.now(timezone.utc).timestamp())}"
    return {"cycle_id": ciclo, "analysis_id": analise}


def _enviar_erro_seguro(erro, contexto):

    try:
        enviar_erro_sistema(erro, contexto=contexto)
    except Exception as erro_alerta:
        registrar_erro(
            f"OPERATOR | falha ao notificar erro em {contexto}: {erro_alerta}"
        )


def _executar_tarefa_segura(nome, tarefa):

    try:
        resultado = tarefa()
        if isinstance(resultado, dict):
            return resultado
        return {"ok": True, "result": resultado}
    except Exception as erro:
        detalhes = traceback.format_exc()[-3000:]
        registrar_erro(
            f"OPERATOR | tarefa {nome} falhou: {erro}\n{detalhes}"
        )
        _enviar_erro_seguro(erro, contexto=f"tarefa do operador: {nome}")
        return {
            "ok": False,
            "error": "OPERATOR_TASK_EXCEPTION",
            "task": nome,
            "details": str(erro),
        }


def _carregar_operador_config():

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if not config.has_section("OPERATOR"):
        return {
            "collector_enabled": True,
            "collector_interval_minutes": 15,
            "analysis_enabled": True,
            "analysis_interval_minutes": 15,
            "daily_learning_enabled": True,
            "daily_learning_time": "23:55",
            "poll_seconds": 60,
            "telegram_status_enabled": True,
            "telegram_status_interval_minutes": 720,
            "telegram_status_on_start": False,
            "demo_execution_enabled": False,
            "demo_execution_interval_minutes": 15,
            "market_session_enabled": True,
            "market_symbol": "XAUUSD",
            "market_tick_stale_seconds": 180,
            "market_pause_poll_seconds": 60,
            "market_restart_delay_seconds": 120,
        }

    operador = config["OPERATOR"]

    return {
        "collector_enabled": operador.get(
            "collector_enabled",
            "true",
        ).lower() == "true",
        "collector_interval_minutes": _ler_inteiro_config(
            operador,
            "collector_interval_minutes",
            15,
        ),
        "analysis_enabled": operador.get(
            "analysis_enabled",
            "true",
        ).lower() == "true",
        "analysis_interval_minutes": _ler_inteiro_config(
            operador,
            "analysis_interval_minutes",
            15,
        ),
        "daily_learning_enabled": operador.get(
            "daily_learning_enabled",
            "true",
        ).lower() == "true",
        "daily_learning_time": _normalizar_horario(
            operador.get("daily_learning_time", "23:55"),
        ),
        "poll_seconds": _ler_inteiro_config(
            operador,
            "poll_seconds",
            60,
        ),
        "telegram_status_enabled": operador.get(
            "telegram_status_enabled",
            "true",
        ).lower() == "true",
        "telegram_status_interval_minutes": _ler_inteiro_config(
            operador,
            "telegram_status_interval_minutes",
            720,
        ),
        "telegram_status_on_start": operador.get(
            "telegram_status_on_start",
            "false",
        ).lower() == "true",
        "demo_execution_enabled": operador.get(
            "demo_execution_enabled",
            "false",
        ).lower() == "true",
        "demo_execution_interval_minutes": _ler_inteiro_config(
            operador,
            "demo_execution_interval_minutes",
            15,
        ),
        "market_session_enabled": operador.get(
            "market_session_enabled",
            "true",
        ).lower() == "true",
        "market_symbol": operador.get(
            "market_symbol",
            "XAUUSD",
        ).strip() or "XAUUSD",
        "market_tick_stale_seconds": _ler_inteiro_config(
            operador,
            "market_tick_stale_seconds",
            180,
            minimo=30,
        ),
        "market_pause_poll_seconds": _ler_inteiro_config(
            operador,
            "market_pause_poll_seconds",
            60,
            minimo=10,
        ),
        "market_restart_delay_seconds": _ler_inteiro_config(
            operador,
            "market_restart_delay_seconds",
            120,
            minimo=30,
        ),
    }


def _resetar_ciclo_apos_reabertura():

    for caminho in (
        COLLECTOR_STATE_FILE,
        ANALYSIS_STATE_FILE,
        DEMO_EXECUTION_STATE_FILE,
        STALE_DATA_STATE_FILE,
    ):
        try:
            caminho.unlink(missing_ok=True)
        except OSError as erro:
            registrar_erro(
                f"OPERATOR | falha ao resetar {caminho.name}: {erro}"
            )


def _avaliar_sessao_corretora(config):

    session = inspect_broker_session(
        symbol=config["market_symbol"],
        stale_tick_seconds=config["market_tick_stale_seconds"],
    )
    state = register_session_status(session)

    if state.get("status_changed"):
        registrar_log(
            "OPERATOR | sessao da corretora mudou: "
            f"{state.get('previous_status')} -> {state['status']} | "
            f"{state['reason']}"
        )

    if state["open"] and state.get("status_changed"):
        restart = restart_mt5_connection(symbol=config["market_symbol"])
        _resetar_ciclo_apos_reabertura()
        registrar_log(
            "OPERATOR | mercado reaberto; motor MT5 reiniciado e "
            f"ciclo completo liberado: {restart}"
        )
        state["reopen_restart"] = restart

    if maintenance_is_due(
        state,
        delay_seconds=config["market_restart_delay_seconds"],
    ):
        restart = restart_mt5_connection(symbol=config["market_symbol"])
        mark_maintenance_done(restart)
        registrar_log(
            "OPERATOR | manutencao da pausa executada; "
            f"motor MT5 reiniciado: {restart}"
        )
        state["maintenance_done"] = True
        state["maintenance_result"] = restart

    return state


def _ler_ultima_execucao():

    if not STATE_FILE.exists():
        return None

    conteudo = _ler_texto_estado(STATE_FILE)

    if not conteudo:
        return None

    try:
        return date.fromisoformat(conteudo)
    except ValueError:
        return None


def _salvar_execucao(data_execucao):

    _escrever_texto_atomico(STATE_FILE, str(data_execucao))


def _ler_ultimo_status_telegram():

    if not STATUS_STATE_FILE.exists():
        return None

    conteudo = _ler_texto_estado(STATUS_STATE_FILE)

    if not conteudo:
        return None

    try:
        return datetime.fromisoformat(conteudo)
    except ValueError:
        return None


def _salvar_status_telegram(agora):

    try:
        _escrever_texto_atomico(
            STATUS_STATE_FILE,
            agora.isoformat(timespec="seconds"),
        )
    except OSError as erro:
        registrar_log(
            "OPERATOR | status Telegram enviado, mas estado nao foi salvo: "
            f"{erro}"
        )
        return False

    return True


def _ler_ultima_coleta():

    if not COLLECTOR_STATE_FILE.exists():
        return None

    conteudo = _ler_texto_estado(COLLECTOR_STATE_FILE)

    if not conteudo:
        return None

    try:
        return datetime.fromisoformat(conteudo)
    except ValueError:
        return None


def _salvar_coleta(agora):

    _escrever_texto_atomico(
        COLLECTOR_STATE_FILE,
        agora.isoformat(timespec="seconds"),
    )


def _ler_ultima_analise():

    if not ANALYSIS_STATE_FILE.exists():
        return None

    conteudo = _ler_texto_estado(ANALYSIS_STATE_FILE)

    if not conteudo:
        return None

    try:
        return datetime.fromisoformat(conteudo)
    except ValueError:
        return None


def _salvar_analise(agora):

    _escrever_texto_atomico(
        ANALYSIS_STATE_FILE,
        agora.isoformat(timespec="seconds"),
    )


def _ler_ultima_execucao_demo():

    if not DEMO_EXECUTION_STATE_FILE.exists():
        return None

    conteudo = _ler_texto_estado(DEMO_EXECUTION_STATE_FILE)

    if not conteudo:
        return None

    try:
        return datetime.fromisoformat(conteudo)
    except ValueError:
        return None


def _salvar_execucao_demo(agora):

    _escrever_texto_atomico(
        DEMO_EXECUTION_STATE_FILE,
        agora.isoformat(timespec="seconds"),
    )


def _deve_coletar(agora, intervalo_minutos):

    ultima_coleta = _ler_ultima_coleta()

    if ultima_coleta is None:
        return True

    segundos = (agora - ultima_coleta).total_seconds()

    return segundos >= intervalo_minutos * 60


def _deve_analisar(agora, intervalo_minutos):

    ultima_analise = _ler_ultima_analise()

    if ultima_analise is None:
        return True

    segundos = (agora - ultima_analise).total_seconds()

    return segundos >= intervalo_minutos * 60


def _deve_executar_demo(agora, intervalo_minutos):

    ultima_execucao = _ler_ultima_execucao_demo()

    if ultima_execucao is None:
        return True

    segundos = (agora - ultima_execucao).total_seconds()

    return segundos >= intervalo_minutos * 60


def _assinatura_conflito():

    from operator_status import obter_status_operadores

    operadores = obter_status_operadores()["operators"]
    alinhamento = operadores["alignment"]
    estrutura = operadores["structure"]
    setup = operadores["setup"]

    if alinhamento.get("status") != "CONFLITO":
        return None

    return "|".join(
        [
            str(estrutura.get("tendencia")),
            str(setup.get("smc")),
            str(setup.get("elliott")),
            str(setup.get("direcao")),
        ]
    )


def _ler_ultimo_conflito():

    if not CONFLICT_STATE_FILE.exists():
        return None

    return _ler_texto_estado(CONFLICT_STATE_FILE) or None


def _salvar_conflito(assinatura):

    _escrever_texto_atomico(CONFLICT_STATE_FILE, assinatura)


def _assinatura_dados_antigos():

    from operator_status import obter_status_operadores

    coletor = obter_status_operadores()["operators"]["collector"]

    if coletor.get("status") != "DADOS ANTIGOS":
        return None

    ultimo_preco = coletor.get("last_price", {})
    ultimo_candle = coletor.get("last_candle", {})

    return "|".join(
        [
            str(ultimo_preco.get("data")),
            str(ultimo_preco.get("bid")),
            str(ultimo_candle.get("data")),
            str(ultimo_candle.get("close")),
        ]
    )


def _ler_ultimo_dado_antigo():

    if not STALE_DATA_STATE_FILE.exists():
        return None

    return _ler_texto_estado(STALE_DATA_STATE_FILE) or None


def _salvar_dado_antigo(assinatura):

    _escrever_texto_atomico(STALE_DATA_STATE_FILE, assinatura)


def _deve_enviar_status_telegram(agora, intervalo_minutos):

    ultimo_envio = _ler_ultimo_status_telegram()

    if ultimo_envio is None:
        return True

    segundos = (agora - ultimo_envio).total_seconds()

    return segundos >= intervalo_minutos * 60


def _segundos_para_status_telegram(agora, intervalo_minutos):

    ultimo_envio = _ler_ultimo_status_telegram()

    if ultimo_envio is None:
        return 0

    segundos = int((agora - ultimo_envio).total_seconds())
    restante = int(intervalo_minutos * 60) - segundos

    return max(0, restante)


def _horario_atingido(agora, horario_configurado):

    hora, minuto = horario_configurado.split(":")
    horario_alvo = agora.replace(
        hour=int(hora),
        minute=int(minuto),
        second=0,
        microsecond=0,
    )

    return agora >= horario_alvo


def _detalhar_falha_subprocesso(resultado):

    stderr = (resultado.stderr or "").strip()
    stdout = (resultado.stdout or "").strip()
    partes = [f"Returncode: {resultado.returncode}"]

    if stderr:
        partes.append(f"STDERR: {stderr[-1200:]}")

    if stdout:
        partes.append(f"STDOUT: {stdout[-1200:]}")

    if len(partes) == 1:
        partes.append(
            "Sem detalhes no terminal. A analise encerrou sem stdout/stderr."
        )

    return "\n".join(partes)


def executar_aprendizado_diario(forcar=False):

    hoje = date.today()
    ultima_execucao = _ler_ultima_execucao()

    if not forcar and ultima_execucao == hoje:
        registrar_log("OPERATOR | aprendizado diario ja executado hoje")
        return {
            "ok": False,
            "error": "DAILY_LEARNING_ALREADY_DONE",
        }

    try:
        relatorio = gerar_relatorio_aprendizado_diario(hoje)
        relatorio_operador = gerar_relatorio_operador_diario(hoje)
        auditoria_setup = generate_setup_audit(hoje)
        resultado_telegram = enviar_relatorio_aprendizado_texto(relatorio)
        enviar_relatorio_aprendizado_texto(relatorio_operador)
        enviar_relatorio_aprendizado_texto(auditoria_setup["text"])
        _salvar_execucao(hoje)
        registrar_log("OPERATOR | aprendizado diario executado")

        return {
            "ok": True,
            "telegram": resultado_telegram,
            "operator_report_size": len(relatorio_operador),
            "setup_audit_status": auditoria_setup["audit"]["status"],
        }

    except Exception as erro:
        registrar_erro(f"OPERATOR | falha no aprendizado diario: {erro}")
        enviar_erro_sistema(
            erro,
            contexto="aprendizado diario",
        )
        return {
            "ok": False,
            "error": "DAILY_LEARNING_FAILED",
            "details": str(erro),
        }


def executar_status_telegram(forcar=False):

    agora = datetime.now()
    config = _carregar_operador_config()

    if (
        not forcar
        and not _deve_enviar_status_telegram(
            agora,
            config["telegram_status_interval_minutes"],
        )
    ):
        restante = _segundos_para_status_telegram(
            agora,
            config["telegram_status_interval_minutes"],
        )
        registrar_log(
            "OPERATOR | status Telegram aguardando intervalo "
            f"({restante}s restantes)"
        )
        return {
            "ok": False,
            "error": "TELEGRAM_STATUS_INTERVAL_WAIT",
            "remaining_seconds": restante,
        }

    try:
        resultado = enviar_status_operadores()

        if resultado.get("ok"):
            _salvar_status_telegram(agora)
            registrar_log("OPERATOR | status Telegram enviado")
        else:
            registrar_erro(
                "OPERATOR | status Telegram nao enviado; "
                f"nova tentativa sera permitida: {resultado}"
            )

        return resultado

    except Exception as erro:
        registrar_erro(f"OPERATOR | falha no status Telegram: {erro}")
        enviar_erro_sistema(
            erro,
            contexto="status dos operadores",
        )
        return {
            "ok": False,
            "error": "TELEGRAM_STATUS_FAILED",
            "details": str(erro),
        }


def executar_coleta_programada(forcar=False):

    agora = datetime.now()
    config = _carregar_operador_config()

    if (
        not forcar
        and not _deve_coletar(
            agora,
            config["collector_interval_minutes"],
        )
    ):
        return {
            "ok": False,
            "error": "COLLECTOR_INTERVAL_WAIT",
        }

    resultado = executar_coleta_manual()

    if resultado.get("ok"):
        _salvar_coleta(agora)
        register_emotional_event("collection_success")
        registrar_contexto_cerebro(
            origem="operator",
            tipo="coleta_programada",
            observacao="Snapshot automatico apos coleta.",
        )
        registrar_log("OPERATOR | coleta programada executada")

    return resultado


def executar_analise_programada(forcar=False):

    agora = datetime.now()
    config = _carregar_operador_config()

    if (
        not forcar
        and not _deve_analisar(
            agora,
            config["analysis_interval_minutes"],
        )
    ):
        return {
            "ok": False,
            "error": "ANALYSIS_INTERVAL_WAIT",
        }

    try:
        ambiente = os.environ.copy()
        ambiente["PYTHONIOENCODING"] = "utf-8"
        ambiente["PYTHONUTF8"] = "1"
        ambiente["PYTHONPATH"] = str(ROOT_DIR)

        comando = [sys.executable, "-B", str(ROOT_DIR / "src" / "leon.py")]
        resultado = subprocess.run(
            comando,
            cwd=str(ROOT_DIR),
            env=ambiente,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=120,
        )

        if (
            resultado.returncode != 0
            and "MemoryError" in (resultado.stderr or "")
        ):
            registrar_log(
                "OPERATOR | memoria insuficiente na analise; "
                "repetindo uma vez apos pausa"
            )
            time.sleep(5)
            resultado = subprocess.run(
                comando,
                cwd=str(ROOT_DIR),
                env=ambiente,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=120,
            )

        if resultado.returncode != 0:
            detalhes = _detalhar_falha_subprocesso(resultado)
            register_emotional_event("error", "Falha na analise automatica.")
            registrar_erro(f"OPERATOR | falha na analise: {detalhes}")
            enviar_erro_sistema(
                detalhes[-1200:],
                contexto="analise automatica",
            )
            return {
                "ok": False,
                "error": "ANALYSIS_FAILED",
                "details": detalhes[-1200:],
            }

        bloqueios_analise = [
            linha.strip()
            for linha in resultado.stdout.splitlines()
            if (
                "ENTRADA BLOQUEADA:" in linha
                or "SEM ENTRADA:" in linha
            )
        ]
        if bloqueios_analise:
            registrar_log(
                "OPERATOR | diagnostico de entrada: "
                + " | ".join(bloqueios_analise[-5:])
            )

        _salvar_analise(agora)
        register_emotional_event("analysis_success")
        avaliacao_pre_operacao = avaliar_pre_operacoes_abertas()
        resultados_avaliados = avaliacao_pre_operacao.get("results", [])
        fechamentos_mt5 = check_mt5_closed_operations()
        ids_executados = set(fechamentos_mt5.get("executed_ids", []))

        for operacao_finalizada in fechamentos_mt5.get("operations", []):
            resultado_real = (
                "ACERTO"
                if str(operacao_finalizada.get("resultado", "")).startswith("WIN")
                else "ERRO"
            )
            try:
                brain_score_real = float(
                    operacao_finalizada.get("brain_score") or 0
                )
            except (TypeError, ValueError):
                brain_score_real = 0
            registrar_performance(resultado_real)
            registrar_brain(
                brain_score_real,
                operacao_finalizada.get("confianca") or "SEM_DADOS",
                resultado_real,
            )
            alerta_fechamento = send_operation_close_alert(operacao_finalizada)
            registrar_log(
                "OPERATOR | alerta final MT5: "
                f"id={operacao_finalizada.get('id')} "
                f"resultado={operacao_finalizada.get('resultado')} "
                f"ok={alerta_fechamento.get('ok', False)} "
                f"erro={alerta_fechamento.get('error', '')}"
            )

        for operacao_finalizada in resultados_avaliados:
            if operacao_finalizada.get("id") in ids_executados:
                continue

            alerta_fechamento = send_operation_close_alert(operacao_finalizada)
            registrar_log(
                "OPERATOR | alerta final de operacao: "
                f"id={operacao_finalizada.get('id')} "
                f"resultado={operacao_finalizada.get('resultado')} "
                f"ok={alerta_fechamento.get('ok', False)} "
                f"erro={alerta_fechamento.get('error', '')}"
            )

        resultados_emocionais = list(fechamentos_mt5.get("operations", []))
        resultados_emocionais.extend(
            item
            for item in resultados_avaliados
            if item.get("id") not in ids_executados
        )

        if any(
            str(item.get("resultado", "")).startswith("WIN")
            for item in resultados_emocionais
        ):
            register_emotional_event("win")
        elif any(
            item.get("resultado") == "LOSS"
            for item in resultados_emocionais
        ):
            register_emotional_event("loss")
        contexto_mercado = registrar_contexto_mercado()
        revisao_blocos = process_operation_batches()
        for revisao in revisao_blocos.get("generated", []):
            resultado_revisao = enviar_revisao_operacoes_texto(
                revisao.get("report")
            )
            registrar_log(
                "OPERATOR | revisao de bloco: "
                f"bloco={revisao.get('batch')} "
                f"ok={resultado_revisao.get('ok', False)} "
                f"erro={resultado_revisao.get('error', '')}"
            )

        registrar_contexto_cerebro(
            origem="operator",
            tipo="analise_programada",
            observacao="Ciclo automatico de analise executado.",
        )
        registrar_log("OPERATOR | analise programada executada")

        return {
            "ok": True,
            "pre_operation": avaliacao_pre_operacao,
            "market_context": contexto_mercado,
            "batch_review": revisao_blocos,
            "output_tail": resultado.stdout[-1500:],
        }

    except Exception as erro:
        register_emotional_event("error", str(erro))
        registrar_erro(f"OPERATOR | falha na analise automatica: {erro}")
        enviar_erro_sistema(
            erro,
            contexto="analise automatica",
        )
        return {
            "ok": False,
            "error": "ANALYSIS_EXCEPTION",
            "details": str(erro),
        }


def executar_ordem_demo_programada(forcar=False):

    agora = datetime.now()
    config = _carregar_operador_config()

    if (
        not forcar
        and not _deve_executar_demo(
            agora,
            config["demo_execution_interval_minutes"],
        )
    ):
        return {
            "ok": False,
            "error": "DEMO_EXECUTION_INTERVAL_WAIT",
        }

    resultado = executar_ordem_mt5_pre_operacao(forcar=False)
    registrar_log(
        "OPERATOR | execucao demo avaliada: "
        f"ok={resultado.get('ok', False)} "
        f"erro={resultado.get('error', '')}"
    )

    if resultado.get("error") == "NO_OPEN_PRE_OPERATION_TO_EXECUTE":
        register_emotional_event("observation")
        ultimo = (resumo_pre_operacao().get("ultimo") or {})
        if ultimo and ultimo.get("status") == "OBSERVADO":
            registrar_relatorio_operacao(
                ultimo,
                decisao="OBSERVAR",
                motivo=ultimo.get("observacao") or "SEM_ENTRADA",
            )
    elif resultado.get("ok"):
        register_emotional_event("demo_entry")
    elif resultado.get("error") in [
        "SETUP_SCORE_BELOW_MINIMUM",
        "LIVE_RR_BELOW_MINIMUM",
        "ENTRY_PRICE_DRIFT_ABOVE_LIMIT",
        "RISK_CONTROL_BLOCKED",
        "SPREAD_ABOVE_LIMIT",
    ]:
        register_emotional_event(
            "blocked",
            f"Protecao acionada: {resultado.get('error')}.",
        )

    if resultado.get("ok") or resultado.get("error") in [
        "MT5_ORDER_ALREADY_SENT_FOR_PRE_OPERATION",
        "NO_OPEN_PRE_OPERATION_TO_EXECUTE",
        "SETUP_SCORE_BELOW_MINIMUM",
        "LIVE_RR_BELOW_MINIMUM",
        "ENTRY_PRICE_DRIFT_ABOVE_LIMIT",
        "RISK_CONTROL_BLOCKED",
        "SPREAD_ABOVE_LIMIT",
    ]:
        _salvar_execucao_demo(agora)

    return resultado


def executar_alerta_conflito(forcar=False):

    assinatura = _assinatura_conflito()

    if assinatura is None:
        return {
            "ok": False,
            "error": "NO_ALIGNMENT_CONFLICT",
        }

    if not forcar and assinatura == _ler_ultimo_conflito():
        registrar_log("OPERATOR | conflito ja alertado")
        return {
            "ok": False,
            "error": "ALIGNMENT_CONFLICT_ALREADY_SENT",
        }

    try:
        resultado = enviar_alerta_conflito_operadores()

        if resultado.get("ok"):
            _salvar_conflito(assinatura)
            registrar_log("OPERATOR | alerta de conflito enviado")

        return resultado

    except Exception as erro:
        registrar_erro(f"OPERATOR | falha no alerta de conflito: {erro}")
        enviar_erro_sistema(
            erro,
            contexto="alerta de conflito",
        )
        return {
            "ok": False,
            "error": "ALIGNMENT_CONFLICT_ALERT_FAILED",
            "details": str(erro),
        }


def executar_alerta_dados_antigos(forcar=False):

    assinatura = _assinatura_dados_antigos()

    if assinatura is None:
        return {
            "ok": False,
            "error": "NO_STALE_COLLECTOR_DATA",
        }

    if not forcar and assinatura == _ler_ultimo_dado_antigo():
        registrar_log("OPERATOR | dados antigos ja alertados")
        return {
            "ok": False,
            "error": "STALE_COLLECTOR_DATA_ALREADY_SENT",
        }

    try:
        resultado = enviar_alerta_dados_antigos()

        if resultado.get("ok"):
            _salvar_dado_antigo(assinatura)
            registrar_log("OPERATOR | alerta de dados antigos enviado")

        return resultado

    except Exception as erro:
        registrar_erro(f"OPERATOR | falha no alerta de dados antigos: {erro}")
        enviar_erro_sistema(
            erro,
            contexto="alerta de dados antigos",
        )
        return {
            "ok": False,
            "error": "STALE_COLLECTOR_DATA_ALERT_FAILED",
            "details": str(erro),
        }


def iniciar_operador():

    config = _carregar_operador_config()
    autonomia = status_autonomia()
    if not autonomia["active"] and autonomia.get("reason") in (
        "AUTONOMY_DISABLED_IN_CONFIG",
        "AUTONOMY_NOT_GRANTED",
    ):
        _auto_config = configparser.ConfigParser()
        _auto_config.read(CONFIG_FILE, encoding="utf-8")
        _auto_section = _auto_config["AUTONOMY"] if _auto_config.has_section("AUTONOMY") else {}
        if str(_auto_section.get("enabled", "false")).lower() == "true":
            _max_min = _auto_section.getint("max_minutes", fallback=1440)
            conceder_autonomia(_max_min)
            registrar_log(
                f"PROFESSOR LEON | autonomia auto-concedida por {_max_min} min"
            )
    autonomia = status_autonomia()
    autonomia_anterior_ativa = autonomia["active"]

    _registrar_heartbeat(
        "INICIANDO",
        {
            "scope": autonomia.get("scope"),
            "expires_at": autonomia.get("expires_at"),
            "execution_authorized": autonomia["active"],
        },
    )
    registrar_log("PROFESSOR LEON | operador iniciado")
    if not autonomia["active"]:
        registrar_log(
            "PROFESSOR LEON | modo observacao 24h; "
            f"execucao bloqueada: {autonomia.get('reason')}"
        )
    register_emotional_event("startup")
    print("===================================")
    print("PROFESSOR LEON ONLINE")
    print("===================================")
    print(f"Coleta automatica: {config['collector_enabled']}")
    print(f"Intervalo coleta: {config['collector_interval_minutes']} min")
    print(f"Analise automatica: {config['analysis_enabled']}")
    print(f"Intervalo analise: {config['analysis_interval_minutes']} min")
    print(f"Aprendizado diario: {config['daily_learning_enabled']}")
    print(f"Horario: {config['daily_learning_time']}")
    print(f"Status Telegram: {config['telegram_status_enabled']}")
    print(f"Execucao demo: {config['demo_execution_enabled']}")
    print(f"Sessao pela corretora: {config['market_session_enabled']}")
    print(f"Simbolo monitorado: {config['market_symbol']}")
    if autonomia["active"]:
        print(f"Autonomia ate: {autonomia['expires_at']}")
    else:
        print("Modo: observacao 24h (execucao bloqueada)")
    print("===================================")

    if config["telegram_status_enabled"] and config["telegram_status_on_start"]:
        resultado_inicial = _executar_tarefa_segura(
            "status_telegram_inicial",
            lambda: executar_status_telegram(forcar=True),
        )
        registrar_log(
            "OPERATOR | status Telegram inicial concluido: "
            f"ok={resultado_inicial.get('ok', False)}"
        )

    try:
        while True:
            autonomia = status_autonomia()

            if autonomia_anterior_ativa and not autonomia["active"]:
                registrar_log(
                    "PROFESSOR LEON | autonomia encerrada; "
                    f"continuando em observacao: {autonomia}"
                )
                resultado_alerta = _executar_tarefa_segura(
                    "alerta_autonomia_encerrada",
                    lambda: enviar_alerta_operador_encerrado(autonomia),
                )
                registrar_log(
                    "PROFESSOR LEON | alerta encerramento Telegram: "
                    f"{resultado_alerta}"
                )
                print("===================================")
                print("AUTONOMIA ENCERRADA")
                print("===================================")
                print(f"Motivo: {autonomia['reason']}")
                print("Execucao bloqueada; analise continua em observacao.")
                print("===================================")
            elif not autonomia_anterior_ativa and autonomia["active"]:
                registrar_log(
                    "PROFESSOR LEON | autonomia ativada; "
                    f"execucao liberada ate {autonomia.get('expires_at')}"
                )

            autonomia_anterior_ativa = autonomia["active"]

            config = _carregar_operador_config()
            agora = datetime.now()
            resultados = {}

            if config["market_session_enabled"]:
                sessao = _avaliar_sessao_corretora(config)
                if not sessao["open"]:
                    _registrar_heartbeat(
                        "PAUSA_MERCADO",
                        {
                            "broker_status": sessao["status"],
                            "reason": sessao["reason"],
                            "last_tick_at": sessao.get("last_tick_at"),
                            "tick_age_seconds": sessao.get(
                                "tick_age_seconds"
                            ),
                            "maintenance_done": sessao.get(
                                "maintenance_done",
                                False,
                            ),
                            "execution_authorized": autonomia["active"],
                        },
                    )
                    time.sleep(config["market_pause_poll_seconds"])
                    continue

            if config["collector_enabled"]:
                resultados["collector"] = _executar_tarefa_segura(
                    "coleta_programada",
                    executar_coleta_programada,
                )

            if config["analysis_enabled"]:
                resultados["analysis"] = _executar_tarefa_segura(
                    "analise_programada",
                    executar_analise_programada,
                )

            if config["demo_execution_enabled"] and autonomia["active"]:
                resultados["demo_execution"] = _executar_tarefa_segura(
                    "execucao_demo",
                    executar_ordem_demo_programada,
                )

            if (
                config["daily_learning_enabled"]
                and _horario_atingido(agora, config["daily_learning_time"])
            ):
                resultados["daily_learning"] = _executar_tarefa_segura(
                    "aprendizado_diario",
                    executar_aprendizado_diario,
                )

            if config["telegram_status_enabled"]:
                resultados["telegram_status"] = _executar_tarefa_segura(
                    "status_telegram",
                    executar_status_telegram,
                )
                resultados["conflict_alert"] = _executar_tarefa_segura(
                    "alerta_conflito",
                    executar_alerta_conflito,
                )
                resultados["stale_data_alert"] = _executar_tarefa_segura(
                    "alerta_dados_antigos",
                    executar_alerta_dados_antigos,
                )

            falhas = [
                nome
                for nome, resultado in resultados.items()
                if (
                    resultado.get("error") == "OPERATOR_TASK_EXCEPTION"
                    or resultado.get("error") == "ANALYSIS_EXCEPTION"
                )
            ]
            _registrar_heartbeat(
                (
                    "DEGRADADO"
                    if falhas
                    else "ONLINE"
                    if autonomia["active"]
                    else "OBSERVACAO"
                ),
                {
                    "scope": autonomia.get("scope"),
                    "execution_authorized": autonomia["active"],
                    "autonomy_reason": autonomia.get("reason"),
                    "failed_tasks": falhas,
                    "next_poll_seconds": config["poll_seconds"],
                },
            )
            time.sleep(config["poll_seconds"])
    except KeyboardInterrupt:
        _registrar_heartbeat("ENCERRADO", {"reason": "KEYBOARD_INTERRUPT"})
        registrar_log("PROFESSOR LEON | encerrado pelo operador humano")


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa o aprendizado diario uma vez e encerra.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignora a trava de execucao diaria.",
    )
    parser.add_argument(
        "--grant-autonomy-minutes",
        type=int,
        help="Concede autonomia temporaria ao Professor LEON.",
    )
    parser.add_argument(
        "--autonomy-status",
        action="store_true",
        help="Mostra o status atual da autonomia.",
    )
    parser.add_argument(
        "--revoke-autonomy",
        action="store_true",
        help="Revoga a autonomia atual.",
    )
    parser.add_argument(
        "--send-status",
        action="store_true",
        help="Envia o status dos operadores pelo Telegram.",
    )
    parser.add_argument(
        "--send-conflict-alert",
        action="store_true",
        help="Envia alerta de conflito de alinhamento pelo Telegram.",
    )
    parser.add_argument(
        "--send-stale-data-alert",
        action="store_true",
        help="Envia alerta de coleta antiga pelo Telegram.",
    )
    parser.add_argument(
        "--collect-now",
        action="store_true",
        help="Executa coleta manual de preco e candle.",
    )
    parser.add_argument(
        "--analysis-now",
        action="store_true",
        help="Executa ciclo de analise agora.",
    )
    parser.add_argument(
        "--execute-mt5-now",
        action="store_true",
        help="Executa ordem teste no MT5 a partir da ultima pre-operacao aberta.",
    )
    parser.add_argument(
        "--release-mt5-attempt",
        action="store_true",
        help="Libera nova tentativa MT5 para a ultima pre-operacao aberta.",
    )
    parser.add_argument(
        "--demo-execute-now",
        action="store_true",
        help="Executa ordem demo programada agora com travas do conselho.",
    )
    args = parser.parse_args()

    if args.grant_autonomy_minutes is not None:
        resultado = conceder_autonomia(args.grant_autonomy_minutes)
        print(resultado)
        return

    if args.autonomy_status:
        print(status_autonomia())
        return

    if args.revoke_autonomy:
        print(revogar_autonomia())
        return

    if args.send_status:
        print(executar_status_telegram(forcar=args.force))
        return

    if args.send_conflict_alert:
        print(executar_alerta_conflito(forcar=args.force))
        return

    if args.send_stale_data_alert:
        print(executar_alerta_dados_antigos(forcar=args.force))
        return

    if args.collect_now:
        print(executar_coleta_programada(forcar=True))
        return

    if args.analysis_now:
        print(executar_analise_programada(forcar=True))
        return

    if args.execute_mt5_now:
        print(executar_ordem_mt5_pre_operacao(forcar=args.force))
        return

    if args.release_mt5_attempt:
        print(liberar_nova_tentativa_mt5())
        return

    if args.demo_execute_now:
        print(executar_ordem_demo_programada(forcar=True))
        return

    if args.once:
        resultado = executar_aprendizado_diario(forcar=args.force)
        print(resultado)
        return

    iniciar_operador()


if __name__ == "__main__":

    main()
