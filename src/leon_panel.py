# ===================================
# LEON CONTROL PANEL
# ===================================

import json
import configparser
import os
import subprocess
import sys
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

from autonomy_guard import (
    conceder_autonomia,
    revogar_autonomia,
    status_autonomia,
)
from brain_context_memory import registrar_observacao_humana
from collector_operator import executar_coleta_manual
from daily_learning_report import gerar_relatorio_aprendizado_diario
from leon_operator import (
    executar_alerta_conflito,
    executar_alerta_dados_antigos,
    executar_analise_programada,
    executar_aprendizado_diario,
    executar_status_telegram,
)
from market_context_agent import revisar_contextos
from institutional_analysis_engine import (
    analyze_elliott_context,
    analyze_smc_context,
)
from mt5_execution_refiner import load_execution_candles
from mt5_monitor import get_mt5_monitor_status
from mt5_order_executor import (
    executar_ordem_mt5_pre_operacao,
    liberar_nova_tentativa_mt5,
)
from operator_council import avaliar_conselho_operadores
from operation_batch_review import latest_batch_status
from operation_readiness import avaliar_prontidao_operacional
from operator_status import obter_status_operadores
from pre_operation_engine import resumo_pre_operacao
from risk_control_agent import calcular_plano_risco, resumo_risco
from risk_method_engine import desempenho_por_metodo
from system_watchdog_agent import analisar_sistema
from telegram_config import CHAT_ID, TELEGRAM_ENABLED, TOKEN
from telegram_alert import enviar_relatorio_aprendizado_diario
from telegram_alert import enviar_status_operadores
from top_down_agent import ultima_leitura_top_down


ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT_DIR / "reports"
LOGS_DIR = ROOT_DIR / "logs"
DATA_DIR = ROOT_DIR / "data"

PORT = 8765
CONFIG_FILE = ROOT_DIR / "config.ini"
OPERATOR_HEARTBEAT_FILE = DATA_DIR / "operator_heartbeat.json"
OPERATOR_RUNTIME_LOG = LOGS_DIR / "operator_runtime.log"
OPERATOR_RUNTIME_ERROR_LOG = LOGS_DIR / "operator_runtime_error.log"


def _operator_running():

    if not OPERATOR_HEARTBEAT_FILE.exists():
        return False

    try:
        heartbeat = json.loads(
            OPERATOR_HEARTBEAT_FILE.read_text(encoding="utf-8")
        )
        updated_at = datetime.fromisoformat(heartbeat["updated_at"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False

    return (
        heartbeat.get("status") in {"INICIANDO", "ONLINE", "DEGRADADO"}
        and datetime.now() - updated_at <= timedelta(minutes=3)
    )


def _garantir_operador_ativo():

    if _operator_running():
        return {
            "ok": True,
            "operator_started": False,
            "operator_status": "ALREADY_RUNNING",
        }

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    stdout = OPERATOR_RUNTIME_LOG.open("a", encoding="utf-8")
    stderr = OPERATOR_RUNTIME_ERROR_LOG.open("a", encoding="utf-8")

    try:
        processo = subprocess.Popen(
            [sys.executable, "-B", str(ROOT_DIR / "src" / "leon_operator.py")],
            cwd=str(ROOT_DIR),
            stdout=stdout,
            stderr=stderr,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as erro:
        return {
            "ok": False,
            "operator_started": False,
            "operator_status": "START_FAILED",
            "details": str(erro),
        }
    finally:
        stdout.close()
        stderr.close()

    return {
        "ok": True,
        "operator_started": True,
        "operator_status": "STARTED",
        "operator_pid": processo.pid,
    }


def _panel_config():

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    panel = config["PANEL"] if config.has_section("PANEL") else {}

    host = os.getenv("LEON_PANEL_HOST") or panel.get("host", "127.0.0.1")
    port = int(os.getenv("LEON_PANEL_PORT") or panel.get("port", "8765"))
    access_key = os.getenv("LEON_PANEL_ACCESS_KEY") or panel.get("access_key", "")
    remote_read_only = (
        os.getenv("LEON_PANEL_REMOTE_READ_ONLY")
        or panel.get("remote_read_only", "true")
    ).lower() == "true"

    return {
        "host": host,
        "port": port,
        "access_key": access_key,
        "remote_read_only": remote_read_only,
    }


def _collaboration_config():

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if not config.has_section("COLLABORATION"):
        return {
            "enabled": False,
            "access_key": "",
            "scope": "study_only",
        }

    collaboration = config["COLLABORATION"]

    return {
        "enabled": collaboration.get("enabled", "false").lower() == "true",
        "access_key": collaboration.get("access_key", ""),
        "scope": collaboration.get("scope", "study_only"),
    }


def _ler_texto(caminho, limite=4000):

    if not caminho.exists():
        return ""

    texto = caminho.read_text(encoding="utf-8", errors="replace").strip()

    if len(texto) <= limite:
        return texto

    return texto[-limite:]


def _ler_logs_painel(caminho, limite=2500):

    if not caminho.exists():
        return ""

    linhas = []

    for linha in caminho.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        if "OPERATOR | status Telegram inicial:" in linha:
            prefixo = linha.split("OPERATOR |", 1)[0]
            linhas.append(
                f"{prefixo}OPERATOR | status Telegram inicial concluido "
                "(detalhes ocultados)"
            )
            continue

        if "MT5 ORDER | print Telegram:" in linha:
            prefixo = linha.split("MT5 ORDER |", 1)[0]
            linhas.append(
                f"{prefixo}MT5 ORDER | print Telegram concluido "
                "(detalhes ocultados)"
            )
            continue

        linhas.append(linha)

    texto = "\n".join(linhas).strip()

    if len(texto) <= limite:
        return texto

    return texto[-limite:]


def _ler_erros_recentes(caminho, horas=2, limite=2500):

    if not caminho.exists():
        return ""

    linhas = [
        linha.strip().lstrip("\ufeff")
        for linha in caminho.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
        if linha.strip().lstrip("\ufeff")
    ]

    if not linhas:
        return ""

    agora = datetime.now()
    limite_tempo = agora - timedelta(hours=horas)
    ultimo_sucesso_analise = _ultimo_sucesso_analise()
    ultimo_sucesso_telegram = _ultimo_sucesso_log(
        "OPERATOR | status Telegram enviado"
    )
    recentes = []
    data_herdada = None

    for linha in linhas:
        data_texto = linha.split(" | ", 1)[0]

        try:
            data_erro = datetime.fromisoformat(data_texto)
        except ValueError:
            data_erro = data_herdada
        else:
            data_herdada = data_erro

        if data_erro is None:
            continue

        if ultimo_sucesso_analise and data_erro < ultimo_sucesso_analise:
            continue

        if (
            ultimo_sucesso_telegram
            and data_erro <= ultimo_sucesso_telegram
            and "telegram" in linha.lower()
        ):
            continue

        if data_erro >= limite_tempo:
            recentes.append(linha)

    if recentes:
        texto = "\n".join(recentes)
    else:
        texto = (
            "Sem erros ativos.\n"
            "Historico preservado em logs/errors.txt."
        )

    if len(texto) <= limite:
        return texto

    return texto[-limite:]


def _ultimo_sucesso_analise():
    return _ultimo_sucesso_log("OPERATOR | analise programada executada")


def _ultimo_sucesso_log(marcador):

    caminho = LOGS_DIR / "leon_log.txt"

    if not caminho.exists():
        return None

    ultimo = None

    for linha in caminho.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        if marcador not in linha:
            continue

        data_texto = linha.split("]", 1)[0].lstrip("[")

        try:
            ultimo = datetime.fromisoformat(data_texto)
        except ValueError:
            continue

    return ultimo


def _status():
    pre_operation = resumo_pre_operacao()
    ultimo_pre = pre_operation.get("ultimo") or {}
    risk_plan = None
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if ultimo_pre.get("status") == "ABERTO":
        risk_plan = calcular_plano_risco(ultimo_pre)

    return {
        "operator_status": obter_status_operadores(),
        "autonomy": status_autonomia(),
        "pre_operation": pre_operation,
        "readiness": avaliar_prontidao_operacional(),
        "council": avaliar_conselho_operadores(),
        "risk_control": resumo_risco(),
        "risk_plan": risk_plan,
        "risk_methods": desempenho_por_metodo(),
        "top_down": ultima_leitura_top_down(),
        "market_context": revisar_contextos(),
        "mt5_monitor": get_mt5_monitor_status(),
        "watchdog": analisar_sistema(),
        "batch_learning": latest_batch_status(),
        "telegram": {
            "enabled": TELEGRAM_ENABLED,
            "has_token": bool(TOKEN),
            "has_chat_id": bool(CHAT_ID),
            "chat_id": CHAT_ID,
            "last_checkpoint": _ler_texto(
                DATA_DIR / "telegram_status_state.txt",
                limite=80,
            ),
        },
        "mode": {
            "study_scope": config.get("AUTONOMY", "scope", fallback="learning_only"),
            "demo_execution": config.get(
                "OPERATOR",
                "demo_execution_enabled",
                fallback="false",
            ),
            "real_blocked": config.get("EXECUTION", "demo_only", fallback="true"),
            "mt5_enabled": config.get("MT5", "enabled", fallback="false"),
        },
        "collaboration": {
            "enabled": _collaboration_config()["enabled"],
            "scope": _collaboration_config()["scope"],
        },
        "daily_learning_state": _ler_texto(
            DATA_DIR / "daily_learning_state.txt",
            limite=100,
        ),
        "daily_learning_report": _ler_texto(
            REPORTS_DIR / "daily_learning_report.txt",
        ),
        "logs": _ler_logs_painel(
            LOGS_DIR / "leon_log.txt",
            limite=2500,
        ),
        "errors": _ler_erros_recentes(
            LOGS_DIR / "errors.txt",
        ),
    }


def _study_chart():
    market = load_execution_candles(
        symbol="XAUUSD",
        m15_count=160,
        m5_count=40,
    )
    if not market.get("ok"):
        return market

    candles = market["m15"]
    smc = analyze_smc_context(candles)
    trend = (
        "ALTA"
        if smc.get("structure_bias") == "BULLISH"
        else "BAIXA"
        if smc.get("structure_bias") == "BEARISH"
        else "LATERAL"
    )
    elliott = analyze_elliott_context(candles, trend)

    visible = candles[-100:]
    offset = len(candles) - len(visible)
    pivots = [
        {
            **pivot,
            "index": pivot["index"] - offset,
        }
        for pivot in smc.get("pivots", [])
        if pivot["index"] >= offset
    ]
    events = [
        {
            **event,
            "index": event["index"] - offset,
        }
        for event in smc.get("events", [])
        if event["index"] >= offset
    ]
    liquidity = dict(smc.get("liquidity") or {})
    if isinstance(liquidity.get("index"), int):
        liquidity["index"] -= offset

    return {
        "ok": True,
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "candles": visible,
        "smc": {
            "smc": smc.get("smc"),
            "bos": smc.get("bos"),
            "choch": smc.get("choch"),
            "fvg": smc.get("fvg"),
            "fvg_zone": smc.get("fvg_zone"),
            "liquidity": liquidity,
            "poi_score": smc.get("poi_score"),
            "reason": smc.get("reason"),
            "pivots": pivots,
            "events": events,
        },
        "elliott": elliott,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def _html():

    return """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LEON Control Panel</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #090b0f;
      --panel: #151922;
      --panel-soft: #10141b;
      --line: #293241;
      --text: #eef1f5;
      --muted: #a9b0ba;
      --accent: #d4af37;
      --danger: #e45b5b;
      --ok: #63c58b;
      --warn: #d4af37;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(212,175,55,.10), transparent 32%),
        linear-gradient(135deg, #090b0f 0%, #101621 55%, #090b0f 100%);
      color: var(--text);
      font-family: Segoe UI, Arial, sans-serif;
    }
    header {
      border-bottom: 1px solid var(--line);
      padding: 22px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      background: rgba(9,11,15,.84);
      position: sticky;
      top: 0;
      z-index: 10;
      backdrop-filter: blur(10px);
    }
    h1 {
      margin: 0;
      font-size: 24px;
      letter-spacing: 0;
    }
    main {
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px;
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 18px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 18px;
      box-shadow: 0 16px 36px rgba(0,0,0,.18);
    }
    h2 {
      margin: 0 0 14px;
      font-size: 16px;
      letter-spacing: 0;
    }
    .stack { display: grid; gap: 18px; }
    .status {
      display: grid;
      gap: 10px;
      color: var(--muted);
      font-size: 14px;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      width: fit-content;
      min-height: 28px;
      padding: 4px 10px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      background: rgba(255,255,255,.03);
    }
    .pill.ok { color: var(--ok); }
    .pill.bad { color: var(--danger); }
    .pill.warn { color: var(--accent); }
    label {
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 8px;
    }
    input {
      width: 100%;
      background: var(--panel-soft);
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 12px;
      font-size: 15px;
    }
    textarea {
      width: 100%;
      min-height: 90px;
      resize: vertical;
      background: var(--panel-soft);
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 12px;
      font-size: 14px;
      font-family: inherit;
    }
    .buttons {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 10px;
      margin-top: 12px;
    }
    button {
      min-height: 40px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #202734;
      color: var(--text);
      cursor: pointer;
      font-weight: 600;
    }
    button.primary {
      background: var(--accent);
      color: #161100;
      border-color: var(--accent);
    }
    button.danger {
      background: #2b2020;
      color: #ffd0d0;
    }
    pre {
      min-height: 190px;
      max-height: 420px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      background: var(--panel-soft);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px;
      color: #d8dde5;
      font-size: 13px;
      line-height: 1.45;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }
    .operators {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .operator-card {
      background: linear-gradient(180deg, #101722 0%, #0d1118 100%);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      min-height: 150px;
    }
    .operator-card.ok { background: linear-gradient(180deg, rgba(99,197,139,.10), #0d1118 70%); }
    .operator-card.warn { background: linear-gradient(180deg, rgba(212,175,55,.10), #0d1118 70%); }
    .operator-card.bad { background: linear-gradient(180deg, rgba(228,91,91,.12), #0d1118 70%); }
    .operator-card h3 {
      margin: 0 0 10px;
      font-size: 15px;
    }
    .operator-card.ok { border-color: rgba(99,197,139,.45); }
    .operator-card.warn { border-color: rgba(212,175,55,.55); }
    .operator-card.bad { border-color: rgba(228,91,91,.6); }
    .operator-card dl {
      margin: 0;
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
    }
    .operator-card div {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid rgba(255,255,255,.04);
      padding-bottom: 4px;
    }
    .operator-card dt { color: var(--muted); }
    .operator-card dd {
      margin: 0;
      color: var(--text);
      text-align: right;
    }
    .stats {
      display: grid;
      gap: 10px;
      color: var(--muted);
      font-size: 14px;
    }
    .stats div,
    .status div {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid rgba(255,255,255,.05);
      padding-bottom: 6px;
    }
    .stats strong,
    .status strong {
      color: var(--text);
      text-align: right;
    }
    .hero-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .hero-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
    }
    .hero-card span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 8px;
    }
    .hero-card strong {
      font-size: 18px;
    }
    #actionResult {
      width: 100%;
      max-width: 100%;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      line-height: 1.4;
    }
    .chart-wrap {
      position: relative;
      width: 100%;
      min-height: 460px;
      background: #0b1017;
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
    }
    #studyChart {
      display: block;
      width: 100%;
      height: 460px;
    }
    .chart-legend {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 12px 0;
      color: var(--muted);
      font-size: 12px;
    }
    .account-change {
      display: none;
      margin-top: 10px;
      color: var(--accent);
    }
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; padding: 16px; }
      header { padding: 18px 16px; align-items: flex-start; flex-direction: column; }
      .grid { grid-template-columns: 1fr; }
      .operators { grid-template-columns: 1fr; }
      .hero-grid { grid-template-columns: 1fr 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>LEON Control Panel</h1>
      <div class="pill">XAUUSD · Professor LEON · learning_only</div>
    </div>
    <div id="autonomyPill" class="pill">Carregando</div>
  </header>

  <main>
    <div class="stack">
      <div class="hero-grid">
        <div class="hero-card">
          <span>Autonomia</span>
          <strong id="heroAutonomy">...</strong>
        </div>
        <div class="hero-card">
          <span>Coletor</span>
          <strong id="heroCollector">...</strong>
        </div>
        <div class="hero-card">
          <span>Semáforo</span>
          <strong id="heroReadiness">...</strong>
        </div>
        <div class="hero-card">
          <span>Telegram</span>
          <strong id="heroTelegram">...</strong>
        </div>
      </div>

      <section>
        <h2>Autonomia</h2>
        <div class="status">
          <div>Status: <strong id="autonomyStatus">...</strong></div>
          <div>Expira em: <strong id="expiresAt">...</strong></div>
          <div>Restante: <strong id="remaining">...</strong></div>
        </div>
        <div style="margin-top: 16px;">
          <label for="minutes">Conceder autonomia por minutos</label>
          <input id="minutes" type="number" min="1" max="1440" value="1440">
          <div class="buttons">
            <button class="primary" onclick="grantAutonomy()">Conceder</button>
            <button class="danger" onclick="revokeAutonomy()">Revogar</button>
          </div>
        </div>
      </section>

      <section>
        <h2>Professor LEON</h2>
        <div class="buttons">
          <button onclick="runLearning()">Gerar relatório</button>
          <button onclick="sendLearning()">Enviar Telegram</button>
          <button onclick="collectNow()">Atualizar coleta</button>
          <button onclick="analysisNow()">Analisar agora</button>
        </div>
        <p id="actionResult" class="pill" style="margin-top: 12px;">Aguardando ação</p>
      </section>

      <section>
        <h2>Estudo Humano</h2>
        <label for="studyKey">Chave de estudo</label>
        <input id="studyKey" type="password" placeholder="Chave autorizada">
        <label for="humanObservation">Observacao para o Professor LEON</label>
        <textarea id="humanObservation" placeholder="Ex: Londres puxou liquidez antes da queda. Observar repeticao desse padrao."></textarea>
        <div class="buttons">
          <button onclick="saveHumanObservation()">Salvar estudo</button>
        </div>
      </section>

      <section>
        <h2>Conselho dos Operadores</h2>
        <div class="status">
          <div>Decisão: <strong id="councilDecision">...</strong></div>
          <div>Resumo: <strong id="councilSummary">...</strong></div>
        </div>
      </section>

      <section>
        <h2>Contexto de Mercado</h2>
        <div class="stats">
          <div>Registros: <strong id="ctxTotal">...</strong></div>
          <div>Última lição: <strong id="ctxLesson">...</strong></div>
        </div>
      </section>

      <section>
        <h2>Top-Down</h2>
        <div class="stats">
          <div>Macro: <strong id="tdMacro">...</strong></div>
          <div>H4: <strong id="tdH4">...</strong></div>
          <div>H1: <strong id="tdH1">...</strong></div>
          <div>M15: <strong id="tdM15">...</strong></div>
          <div>Alinhamento: <strong id="tdAlignment">...</strong></div>
        </div>
      </section>

      <section>
        <h2>Gestor de Risco</h2>
        <div class="stats">
          <div>Status: <strong id="riskEnabled">...</strong></div>
          <div>Saldo: <strong id="riskBalance">...</strong></div>
          <div>Risco por entrada: <strong id="riskPercent">...</strong></div>
          <div>Método: <strong id="riskMethod">...</strong></div>
          <div>Alvo: <strong id="riskTarget">...</strong></div>
          <div>Risco estimado: <strong id="riskEstimated">...</strong></div>
          <div>Lote calculado: <strong id="riskLot">...</strong></div>
          <div>Limite diário: <strong id="dailyLoss">...</strong></div>
          <div>Lote máx.: <strong id="maxLot">...</strong></div>
        </div>
      </section>

      <section>
        <h2>Monitor MT5</h2>
        <div class="stats">
          <div>Conexão: <strong id="mt5Connected">...</strong></div>
          <div>Conta: <strong id="mt5Account">...</strong></div>
          <div>Servidor: <strong id="mt5Server">...</strong></div>
          <div>Modo: <strong id="mt5Mode">...</strong></div>
          <div>Saldo: <strong id="mt5Balance">...</strong></div>
          <div>Equity: <strong id="mt5Equity">...</strong></div>
          <div>Resultado aberto: <strong id="mt5Profit">...</strong></div>
          <div>Posições: <strong id="mt5PositionCount">...</strong></div>
          <div>XAUUSD Bid/Ask: <strong id="mt5Price">...</strong></div>
        </div>
        <div id="accountChanged" class="account-change">
          Conta MT5 alterada. Dados e gráfico foram atualizados.
        </div>
        <div class="buttons">
          <button onclick="refreshAccount()">Atualizar conta MT5</button>
          <button onclick="openTradingView()">Abrir TradingView</button>
        </div>
        <pre id="mt5Positions">Carregando posições...</pre>
      </section>

      <section>
        <h2>Semáforo Operacional</h2>
        <div class="status">
          <div>Nível: <strong id="readinessLevel">...</strong></div>
          <div>Resumo: <strong id="readinessSummary">...</strong></div>
          <div>Regra: <strong id="readinessRules">...</strong></div>
        </div>
      </section>

      <section>
        <h2>Pré-Operação</h2>
        <div class="stats">
          <div>Total: <strong id="preTotal">...</strong></div>
          <div>Observações: <strong id="preObservations">...</strong></div>
          <div>Simulações: <strong id="preSimulations">...</strong></div>
          <div>Abertas: <strong id="preOpen">...</strong></div>
          <div>Fechadas: <strong id="preClosed">...</strong></div>
          <div>Taxa: <strong id="preWinrate">...</strong></div>
        </div>
        <div class="buttons">
          <button class="danger" onclick="executeMt5Test()">Executar teste MT5</button>
          <button onclick="releaseMt5Attempt()">Liberar nova tentativa</button>
        </div>
      </section>

      <section>
        <h2>Telegram</h2>
        <div class="status">
          <div>Ativo: <strong id="telegramEnabled">...</strong></div>
          <div>Token: <strong id="telegramToken">...</strong></div>
          <div>Chat ID: <strong id="telegramChat">...</strong></div>
          <div>Proximo status: <strong id="telegramNext">...</strong></div>
          <div>Último checkpoint: <strong id="telegramLast">...</strong></div>
          <div>Modo: <strong id="operatorMode">...</strong></div>
        </div>
        <div class="buttons">
          <button onclick="sendOperatorStatus()">Enviar status</button>
          <button onclick="sendOperatorHeartbeat()">Heartbeat</button>
          <button onclick="sendConflictAlert()">Alerta conflito</button>
          <button onclick="sendStaleDataAlert()">Alerta coleta</button>
        </div>
      </section>
    </div>

    <div class="stack">
      <section>
        <h2>Estudo Visual M15</h2>
        <div class="chart-legend">
          <span>Verde/vermelho: candles</span>
          <span>Dourado: pivôs</span>
          <span>Azul: BOS</span>
          <span>Roxo: CHOCH</span>
          <span>Área: FVG</span>
          <span>Laranja: sweep</span>
        </div>
        <div class="chart-wrap">
          <canvas id="studyChart"></canvas>
        </div>
        <div class="stats" style="margin-top: 12px;">
          <div>SMC: <strong id="chartSmc">...</strong></div>
          <div>POI: <strong id="chartPoi">...</strong></div>
          <div>Elliott: <strong id="chartElliott">...</strong></div>
          <div>Invalidação: <strong id="chartInvalidation">...</strong></div>
          <div>Atualizado: <strong id="chartUpdated">...</strong></div>
        </div>
      </section>

      <section>
        <h2>Status dos Operadores</h2>
        <div id="operators" class="operators"></div>
      </section>

      <section>
        <h2>Agente Watchdog</h2>
        <div id="watchdog"></div>
      </section>

      <section>
        <h2>Relatório de Aprendizado</h2>
        <pre id="dailyReport">Carregando...</pre>
      </section>

      <div class="grid">
        <section>
          <h2>Logs</h2>
          <pre id="logs">Carregando...</pre>
        </section>
        <section>
          <h2>Erros Ativos</h2>
          <pre id="errors">Carregando...</pre>
        </section>
      </div>
    </div>
  </main>

  <script>
    const panelUrl = new URL(window.location.href);
    const panelKey = panelUrl.searchParams.get("key") || localStorage.getItem("LEON_PANEL_KEY") || "";

    if (panelKey) {
      localStorage.setItem("LEON_PANEL_KEY", panelKey);
    }
    let currentAccountFingerprint =
      localStorage.getItem("LEON_MT5_ACCOUNT_FINGERPRINT") || "";

    async function api(path, options = {}) {
      const headers = Object.assign({}, options.headers || {});
      if (panelKey) headers["X-LEON-PANEL-KEY"] = panelKey;
      const response = await fetch(path, Object.assign({}, options, { headers }));
      return response.json();
    }

    function formatRemaining(seconds) {
      if (!seconds && seconds !== 0) return "Sem autonomia";
      const minutes = Math.floor(seconds / 60);
      const rest = seconds % 60;
      return `${minutes}m ${rest}s`;
    }

    function showResult(result) {
      const messages = {
        "MT5_EXECUTION_DISABLED": "Execução MT5 desligada.",
        "NO_OPEN_PRE_OPERATION_TO_EXECUTE": "Sem pré-operação aberta para executar.",
        "MT5_ORDER_ALREADY_SENT_FOR_PRE_OPERATION": "Tentativa MT5 já feita para esta pré-operação. Use liberar nova tentativa se quiser repetir.",
        "NO_MT5_ATTEMPT_FOUND_FOR_PRE_OPERATION": "Nenhuma tentativa MT5 encontrada para liberar.",
        "MAX_DEMO_ORDERS_DAY_REACHED": "Limite diário de operações demo atingido.",
        "DEMO_EXECUTION_INTERVAL_WAIT": "Aguardando intervalo da execução demo.",
        "MT5_REAL_ACCOUNT_BLOCKED": "Conta real bloqueada. Use apenas demo.",
        "SPREAD_ABOVE_LIMIT": "Spread acima do limite.",
      };
      const status = result.ok ? "OK" : "Aguardando/Bloqueado";
      const detail = result.error ? (messages[result.error] || result.error) : "Ação concluída.";
      document.getElementById("actionResult").textContent = `${status}: ${detail}`;
    }

    function renderOperator(title, data, fields) {
      const bad = ["CONFLITO", "DADOS ANTIGOS", "SEM DADOS", "DESLIGADO"].includes(data.status);
      const warn = ["ATENCAO", "OBSERVANDO", "AGUARDANDO"].includes(data.status);
      const className = bad ? "bad" : (warn ? "warn" : "ok");
      const lines = fields.map(([label, value]) => {
        const content = value || "...";
        return `<div><dt>${label}</dt><dd>${content}</dd></div>`;
      }).join("");
      return `
        <article class="operator-card ${className}">
          <h3>${title}</h3>
          <span class="pill ${className}">${data.status || "..."}</span>
          <p style="color: var(--muted); font-size: 13px;">${data.summary || ""}</p>
          <dl>${lines}</dl>
        </article>
      `;
    }

    function renderOperators(status) {
      const operators = status.operator_status.operators;
      const html = [
        renderOperator("Coletor", operators.collector, [
          ["Preço", operators.collector.last_price?.bid],
          ["Ask", operators.collector.last_price?.ask],
          ["Último", operators.collector.last_price?.idade],
          ["Candles", operators.collector.candle_records],
        ]),
        renderOperator("Estrutura", operators.structure, [
          ["Tendência", operators.structure.tendencia],
          ["Score", operators.structure.score],
          ["Sinal", operators.structure.sinal],
        ]),
        renderOperator("Setup Hunter", operators.setup, [
          ["Direção", operators.setup.direcao],
          ["SMC", operators.setup.smc],
          ["Elliott", operators.setup.elliott],
          ["Confiança", operators.setup.confianca],
        ]),
        renderOperator("Alinhamento", operators.alignment, [
          ["Leitura", operators.alignment.alinhamento],
          ["Direção", operators.alignment.direcao],
          ["Esperada", operators.alignment.direcao_esperada],
          ["Elliott", operators.alignment.elliott],
        ]),
        renderOperator("Risk Manager", operators.risk, [
          ["Máx. trades", operators.risk.max_trades_day],
          ["Score operacional", operators.risk.min_setup_score],
        ]),
        renderOperator("Professor LEON", operators.professor, [
          ["Memória", operators.professor.trade_records],
          ["Brain", operators.professor.brain_records],
          ["Autonomia", operators.professor.autonomy.reason],
          ["Emoção", operators.professor.emotion?.emotion],
          ["Intensidade", `${operators.professor.emotion?.intensity ?? 0}%`],
          ["Pensamento", operators.professor.emotion?.message],
          ["Blocos revisados", status.batch_learning?.processed_batches?.length ?? 0],
          ["Operações válidas", status.batch_learning?.closed_operations ?? 0],
          ["Progresso", `${status.batch_learning?.pending_for_next_batch ?? 0}/20`],
          ["Último", operators.professor.last_brain?.resultado],
        ]),
        renderOperator("Telegram", operators.telegram, [
          ["Ativo", operators.telegram.enabled ? "SIM" : "NAO"],
          ["Token", operators.telegram.has_token ? "OK" : "FALTA"],
          ["Chat ID", operators.telegram.has_chat_id ? "OK" : "FALTA"],
          ["Proximo", operators.telegram.next_heartbeat],
        ]),
      ].join("");
      document.getElementById("operators").innerHTML = html;
    }

    function renderWatchdog(data) {
      const status = data.watchdog || {};
      const events = status.events || [];
      const bad = status.status === "CRITICO";
      const warn = status.status === "ATENCAO";
      const className = bad ? "bad" : (warn ? "warn" : "ok");
      const rows = events.length
        ? events.map((event) => {
            return `<div><dt>${event.level} / ${event.source}</dt><dd>${event.message}</dd></div>`;
          }).join("")
        : "<div><dt>Status</dt><dd>Sem bugs recentes detectados.</dd></div>";

      document.getElementById("watchdog").innerHTML = `
        <article class="operator-card ${className}">
          <h3>${status.name || "Agente Watchdog"}</h3>
          <span class="pill ${className}">${status.status || "..."}</span>
          <p style="color: var(--muted); font-size: 13px;">${status.summary || ""}</p>
          <dl>
            <div><dt>Analise</dt><dd>${status.checks?.analise_minutos ?? "..."} min</dd></div>
            <div><dt>Coleta</dt><dd>${status.checks?.coleta_minutos ?? "..."} min</dd></div>
            <div><dt>Telegram</dt><dd>${status.checks?.telegram_minutos ?? "..."} min</dd></div>
            <div><dt>Telegram alerta</dt><dd>${status.telegram_notify ? "SIM" : "NAO"}</dd></div>
            ${rows}
          </dl>
        </article>
      `;
    }

    function renderMt5(data) {
      const monitor = data.mt5_monitor || {};
      const account = monitor.account || {};
      const market = monitor.market || {};
      const positions = monitor.positions || [];
      const nextFingerprint = account.fingerprint || "";

      if (
        currentAccountFingerprint
        && nextFingerprint
        && currentAccountFingerprint !== nextFingerprint
      ) {
        const notice = document.getElementById("accountChanged");
        notice.style.display = "block";
        setTimeout(() => { notice.style.display = "none"; }, 12000);
        refreshChart();
      }
      if (nextFingerprint) {
        currentAccountFingerprint = nextFingerprint;
        localStorage.setItem(
          "LEON_MT5_ACCOUNT_FINGERPRINT",
          nextFingerprint
        );
      }

      document.getElementById("mt5Connected").textContent =
        monitor.connected ? "CONECTADO" : "DESCONECTADO";
      document.getElementById("mt5Account").textContent = account.login || "...";
      document.getElementById("mt5Server").textContent = account.server || "...";
      document.getElementById("mt5Mode").textContent = account.mode || "...";
      document.getElementById("mt5Balance").textContent =
        account.balance ?? "...";
      document.getElementById("mt5Equity").textContent =
        account.equity ?? "...";
      document.getElementById("mt5Profit").textContent =
        `${monitor.open_profit ?? 0} ${account.currency || ""}`;
      document.getElementById("mt5PositionCount").textContent =
        monitor.position_count ?? 0;
      document.getElementById("mt5Price").textContent =
        `${market.bid ?? "..."} / ${market.ask ?? "..."}`;

      const lines = positions.length
        ? positions.map((position) => [
            `${position.direction} · ${position.volume} lote`,
            `Ticket: ${position.ticket}`,
            `Entrada: ${position.entry} | Atual: ${position.current}`,
            `Stop: ${position.stop} | Alvo: ${position.target}`,
            `Resultado: ${position.profit} ${account.currency || ""}`,
          ].join("\\n")).join("\\n\\n")
        : "Nenhuma posição aberta no XAUUSD.";

      document.getElementById("mt5Positions").textContent = lines;
    }

    function priceToY(price, minPrice, maxPrice, height, padding) {
      const range = Math.max(maxPrice - minPrice, 0.0001);
      return padding + ((maxPrice - price) / range) * (height - padding * 2);
    }

    function drawStudyChart(payload) {
      const canvas = document.getElementById("studyChart");
      const ratio = window.devicePixelRatio || 1;
      const width = Math.max(700, canvas.parentElement.clientWidth);
      const height = 460;
      canvas.width = Math.floor(width * ratio);
      canvas.height = Math.floor(height * ratio);
      const context = canvas.getContext("2d");
      context.scale(ratio, ratio);
      const padding = 34;
      const candles = payload.candles || [];

      context.clearRect(0, 0, width, height);
      if (!candles.length) {
        context.fillStyle = "#a9b0ba";
        context.fillText("Sem candles M15 disponíveis.", 20, 30);
        return;
      }

      const prices = candles.flatMap((item) => [item.high, item.low]);
      const zone = payload.smc?.fvg_zone;
      if (zone) prices.push(zone.start, zone.end);
      const minPrice = Math.min(...prices);
      const maxPrice = Math.max(...prices);
      const candleWidth = (width - padding * 2) / candles.length;

      context.strokeStyle = "rgba(255,255,255,.06)";
      for (let row = 0; row <= 5; row += 1) {
        const y = padding + row * ((height - padding * 2) / 5);
        context.beginPath();
        context.moveTo(padding, y);
        context.lineTo(width - padding, y);
        context.stroke();
      }

      if (zone) {
        const top = priceToY(Math.max(zone.start, zone.end), minPrice, maxPrice, height, padding);
        const bottom = priceToY(Math.min(zone.start, zone.end), minPrice, maxPrice, height, padding);
        context.fillStyle = "rgba(75,130,220,.14)";
        context.fillRect(padding, top, width - padding * 2, Math.max(2, bottom - top));
      }

      candles.forEach((item, index) => {
        const x = padding + index * candleWidth + candleWidth / 2;
        const high = priceToY(item.high, minPrice, maxPrice, height, padding);
        const low = priceToY(item.low, minPrice, maxPrice, height, padding);
        const open = priceToY(item.open, minPrice, maxPrice, height, padding);
        const close = priceToY(item.close, minPrice, maxPrice, height, padding);
        const color = item.close >= item.open ? "#63c58b" : "#e45b5b";
        context.strokeStyle = color;
        context.fillStyle = color;
        context.beginPath();
        context.moveTo(x, high);
        context.lineTo(x, low);
        context.stroke();
        context.fillRect(
          x - Math.max(1, candleWidth * .28),
          Math.min(open, close),
          Math.max(2, candleWidth * .56),
          Math.max(2, Math.abs(close - open))
        );
      });

      (payload.smc?.pivots || []).forEach((pivot) => {
        if (pivot.index < 0 || pivot.index >= candles.length) return;
        const x = padding + pivot.index * candleWidth + candleWidth / 2;
        const y = priceToY(pivot.price, minPrice, maxPrice, height, padding);
        context.fillStyle = "#d4af37";
        context.beginPath();
        context.arc(x, y, 3, 0, Math.PI * 2);
        context.fill();
      });

      (payload.smc?.events || []).forEach((event) => {
        if (event.index < 0 || event.index >= candles.length) return;
        const x = padding + event.index * candleWidth + candleWidth / 2;
        const y = priceToY(event.level, minPrice, maxPrice, height, padding);
        context.fillStyle = event.type.startsWith("CHOCH") ? "#b084f5" : "#62a8ff";
        context.font = "11px Segoe UI";
        context.fillText(event.type.replace("_", " "), x + 3, y - 5);
      });

      const liquidity = payload.smc?.liquidity || {};
      if (Number.isInteger(liquidity.index) && liquidity.index >= 0) {
        const x = padding + liquidity.index * candleWidth + candleWidth / 2;
        const y = priceToY(liquidity.level, minPrice, maxPrice, height, padding);
        context.fillStyle = "#f0a64a";
        context.fillText(liquidity.type.replaceAll("_", " "), x + 3, y + 14);
      }

      if (payload.elliott?.invalidation != null) {
        const y = priceToY(payload.elliott.invalidation, minPrice, maxPrice, height, padding);
        context.setLineDash([6, 5]);
        context.strokeStyle = "#e8d16b";
        context.beginPath();
        context.moveTo(padding, y);
        context.lineTo(width - padding, y);
        context.stroke();
        context.setLineDash([]);
        context.fillStyle = "#e8d16b";
        context.fillText("Invalidação Elliott", padding + 4, y - 5);
      }
    }

    async function refreshChart() {
      const payload = await api("/api/study-chart");
      if (!payload.ok) return;
      drawStudyChart(payload);
      document.getElementById("chartSmc").textContent =
        `${payload.smc.smc} | ${payload.smc.bos} | ${payload.smc.choch}`;
      document.getElementById("chartPoi").textContent =
        `${payload.smc.poi_score}/100 | ${payload.smc.reason}`;
      document.getElementById("chartElliott").textContent =
        `${payload.elliott.label} | ${payload.elliott.phase}`;
      document.getElementById("chartInvalidation").textContent =
        payload.elliott.invalidation ?? "SEM NÍVEL";
      document.getElementById("chartUpdated").textContent = payload.generated_at;
    }

    async function refreshAccount() {
      const result = await api("/api/mt5/refresh-account", { method: "POST" });
      showResult(result);
      await refresh();
      await refreshChart();
    }

    function openTradingView() {
      window.open(
        "https://www.tradingview.com/chart/?symbol=OANDA%3AXAUUSD",
        "_blank",
        "noopener"
      );
    }

    async function refresh() {
      const data = await api("/api/status");
      const autonomy = data.autonomy;
      const active = autonomy.active;
      const pill = document.getElementById("autonomyPill");
      pill.textContent = active ? "Autonomia ativa" : "Autonomia bloqueada";
      pill.className = active ? "pill ok" : "pill bad";
      document.getElementById("autonomyStatus").textContent = autonomy.reason || "...";
      document.getElementById("expiresAt").textContent = autonomy.expires_at || "...";
      document.getElementById("remaining").textContent = formatRemaining(autonomy.remaining_seconds);
      document.getElementById("heroAutonomy").textContent = active ? "ATIVA" : "BLOQUEADA";
      document.getElementById("heroCollector").textContent = data.operator_status.operators.collector.status || "...";
      document.getElementById("heroReadiness").textContent = data.readiness.nivel || "...";
      document.getElementById("heroTelegram").textContent = data.telegram.enabled ? "ATIVO" : "OFF";
      document.getElementById("telegramEnabled").textContent = data.telegram.enabled ? "SIM" : "NAO";
      document.getElementById("telegramToken").textContent = data.telegram.has_token ? "CONFIGURADO" : "NAO ENCONTRADO";
      document.getElementById("telegramChat").textContent = data.telegram.has_chat_id ? "CONFIGURADO" : "NAO ENCONTRADO";
      document.getElementById("telegramNext").textContent = data.operator_status.operators.telegram.next_heartbeat || "...";
      document.getElementById("telegramLast").textContent = data.telegram.last_checkpoint || "...";
      document.getElementById("operatorMode").textContent = data.mode.real_blocked === "true" ? "ESTUDO/DEMO" : "ATENCAO: REAL";
      document.getElementById("preTotal").textContent = data.pre_operation.total;
      document.getElementById("preObservations").textContent = data.pre_operation.observacoes;
      document.getElementById("preSimulations").textContent = data.pre_operation.simulacoes;
      document.getElementById("preOpen").textContent = data.pre_operation.abertos;
      document.getElementById("preClosed").textContent = data.pre_operation.fechados;
      document.getElementById("preWinrate").textContent = `${data.pre_operation.taxa}%`;
      document.getElementById("readinessLevel").textContent = data.readiness.nivel;
      document.getElementById("readinessSummary").textContent = data.readiness.resumo;
      document.getElementById("readinessRules").textContent = `${data.readiness.rules.min_closed} simulações / ${data.readiness.rules.min_winrate}%`;
      document.getElementById("riskEnabled").textContent = data.risk_control.enabled ? "ATIVO" : "DESLIGADO";
      document.getElementById("riskBalance").textContent = data.risk_control.balance ?? "SEM MT5";
      document.getElementById("riskPercent").textContent = `${data.risk_control.method_risk_percent}%`;
      document.getElementById("riskMethod").textContent = data.risk_control.method;
      document.getElementById("riskTarget").textContent =
        data.risk_control.method_rr_target == null
          ? "TÉCNICO SMC (VARIÁVEL)"
          : `1:${data.risk_control.method_rr_target}`;
      document.getElementById("riskEstimated").textContent = data.risk_plan ? `${data.risk_plan.estimated_risk} (${data.risk_plan.estimated_risk_percent}%)` : "SEM ENTRADA";
      document.getElementById("riskLot").textContent = data.risk_plan ? `${data.risk_plan.lot} / calc ${data.risk_plan.calculated_lot}` : "SEM ENTRADA";
      document.getElementById("dailyLoss").textContent = `${data.risk_control.daily_loss_percent}%`;
      document.getElementById("maxLot").textContent = data.risk_control.max_lot;
      document.getElementById("councilDecision").textContent = data.council.decision;
      document.getElementById("councilSummary").textContent = data.council.summary;
      document.getElementById("tdMacro").textContent = data.top_down.macro_semanal;
      document.getElementById("tdH4").textContent = data.top_down.h4_bias;
      document.getElementById("tdH1").textContent = data.top_down.h1_contexto;
      document.getElementById("tdM15").textContent = data.top_down.m15_gatilho;
      document.getElementById("tdAlignment").textContent = data.top_down.alinhamento;
      document.getElementById("ctxTotal").textContent = data.market_context.total;
      document.getElementById("ctxLesson").textContent = data.market_context.last_lesson || data.market_context.summary;
      renderOperators(data);
      renderWatchdog(data);
      renderMt5(data);
      document.getElementById("dailyReport").textContent = data.daily_learning_report || "Sem relatório ainda.";
      document.getElementById("logs").textContent = data.logs || "Sem logs.";
      document.getElementById("errors").textContent = data.errors || "Sem erros.";
    }

    async function grantAutonomy() {
      const minutes = document.getElementById("minutes").value;
      const result = await api("/api/autonomy/grant", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `minutes=${encodeURIComponent(minutes)}`
      });
      showResult(result);
      refresh();
    }

    async function revokeAutonomy() {
      const result = await api("/api/autonomy/revoke", { method: "POST" });
      showResult(result);
      refresh();
    }

    async function runLearning() {
      const result = await api("/api/learning/run", { method: "POST" });
      showResult(result);
      refresh();
    }

    async function collectNow() {
      const result = await api("/api/collector/run", { method: "POST" });
      showResult(result);
      refresh();
    }

    async function analysisNow() {
      const result = await api("/api/analysis/run", { method: "POST" });
      showResult(result);
      refresh();
    }

    async function executeMt5Test() {
      const result = await api("/api/mt5/execute-test", { method: "POST" });
      showResult(result);
      refresh();
    }

    async function releaseMt5Attempt() {
      const result = await api("/api/mt5/release-attempt", { method: "POST" });
      showResult(result);
      refresh();
    }

    async function sendLearning() {
      const result = await api("/api/learning/send", { method: "POST" });
      showResult(result);
      refresh();
    }

    async function saveHumanObservation() {
      const key = document.getElementById("studyKey").value;
      const observation = document.getElementById("humanObservation").value;
      const result = await api("/api/study/observation", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `access_key=${encodeURIComponent(key)}&observation=${encodeURIComponent(observation)}`
      });
      showResult(result);
      if (result.ok) {
        document.getElementById("humanObservation").value = "";
      }
      refresh();
    }

    async function sendOperatorStatus() {
      const result = await api("/api/operators/send", { method: "POST" });
      showResult(result);
      refresh();
    }

    async function sendOperatorHeartbeat() {
      const result = await api("/api/operator/send-status", { method: "POST" });
      showResult(result);
      refresh();
    }

    async function sendConflictAlert() {
      const result = await api("/api/operator/send-conflict-alert", { method: "POST" });
      showResult(result);
      refresh();
    }

    async function sendStaleDataAlert() {
      const result = await api("/api/operator/send-stale-data-alert", { method: "POST" });
      showResult(result);
      refresh();
    }

    refresh();
    refreshChart();
    setInterval(refresh, 10000);
    setInterval(refreshChart, 30000);
    window.addEventListener("resize", () => {
      clearTimeout(window.leonChartResizeTimer);
      window.leonChartResizeTimer = setTimeout(refreshChart, 250);
    });
  </script>
</body>
</html>"""


class LeonPanelHandler(BaseHTTPRequestHandler):

    def _request_path(self):

        return urlparse(self.path).path

    def _query(self):

        return parse_qs(urlparse(self.path).query)

    def _is_local_request(self):

        return self.client_address[0] in {"127.0.0.1", "::1", "localhost"}

    def _is_authorized(self):

        panel = _panel_config()
        access_key = panel["access_key"]

        if self._is_local_request():
            return True

        if not access_key:
            return False

        header_key = self.headers.get("X-LEON-PANEL-KEY", "").strip()
        query_key = self._query().get("key", [""])[0].strip()

        return header_key == access_key or query_key == access_key

    def _is_remote_read_only_blocked(self):

        panel = _panel_config()
        return (
            panel["remote_read_only"]
            and not self._is_local_request()
            and self.command != "GET"
        )

    def _send_forbidden(self, error="PANEL_ACCESS_DENIED"):

        self._send_json({"ok": False, "error": error}, status=403)

    def _send_html(self, conteudo):

        dados = conteudo.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def _send_json(self, payload, status=200):

        dados = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def _body(self):

        tamanho = int(self.headers.get("Content-Length", "0"))
        if tamanho == 0:
            return {}

        texto = self.rfile.read(tamanho).decode("utf-8")
        return parse_qs(texto)

    def log_message(self, format, *args):

        return

    def do_GET(self):

        path = self._request_path()

        if path == "/":
            if not self._is_authorized():
                self._send_forbidden()
                return

            self._send_html(_html())
            return

        if not self._is_authorized():
            self._send_forbidden()
            return

        if path == "/api/status":
            self._send_json(_status())
            return

        if path == "/api/operators":
            self._send_json(obter_status_operadores())
            return

        if path == "/api/study-chart":
            self._send_json(_study_chart())
            return

        self._send_json({"ok": False, "error": "NOT_FOUND"}, status=404)

    def do_POST(self):

        path = self._request_path()

        if not self._is_authorized():
            self._send_forbidden()
            return

        if self._is_remote_read_only_blocked():
            self._send_forbidden("REMOTE_PANEL_READ_ONLY")
            return

        if path == "/api/autonomy/grant":
            body = self._body()
            try:
                minutos = int(body.get("minutes", ["0"])[0])
            except (TypeError, ValueError):
                self._send_json({
                    "ok": False,
                    "error": "AUTONOMY_INVALID_MINUTES",
                })
                return

            resultado = conceder_autonomia(minutos)
            if resultado.get("ok"):
                resultado["operator"] = _garantir_operador_ativo()
            self._send_json(resultado)
            return

        if path == "/api/autonomy/revoke":
            self._send_json(revogar_autonomia())
            return

        if path == "/api/learning/run":
            relatorio = gerar_relatorio_aprendizado_diario()
            self._send_json({"ok": True, "report_size": len(relatorio)})
            return

        if path == "/api/collector/run":
            self._send_json(executar_coleta_manual())
            return

        if path == "/api/analysis/run":
            self._send_json(executar_analise_programada(forcar=True))
            return

        if path == "/api/mt5/execute-test":
            self._send_json(executar_ordem_mt5_pre_operacao(forcar=False))
            return

        if path == "/api/mt5/release-attempt":
            self._send_json(liberar_nova_tentativa_mt5())
            return

        if path == "/api/mt5/refresh-account":
            self._send_json({
                "ok": True,
                "mt5_monitor": get_mt5_monitor_status(),
            })
            return

        if path == "/api/study/observation":
            body = self._body()
            access_key = body.get("access_key", [""])[0].strip()
            observacao = body.get("observation", [""])[0].strip()
            collaboration = _collaboration_config()

            if not collaboration["enabled"]:
                self._send_json({
                    "ok": False,
                    "error": "COLLABORATION_DISABLED",
                })
                return

            if access_key != collaboration["access_key"]:
                self._send_json({
                    "ok": False,
                    "error": "INVALID_STUDY_KEY",
                })
                return

            if not observacao:
                self._send_json({
                    "ok": False,
                    "error": "EMPTY_OBSERVATION",
                })
                return

            linha = registrar_observacao_humana(observacao)
            self._send_json({
                "ok": True,
                "saved": linha,
            })
            return

        if path == "/api/learning/send":
            self._send_json(enviar_relatorio_aprendizado_diario())
            return

        if path == "/api/operator/run-once":
            self._send_json(executar_aprendizado_diario())
            return

        if path == "/api/operators/send":
            self._send_json(enviar_status_operadores())
            return

        if path == "/api/operator/send-status":
            self._send_json(executar_status_telegram(forcar=True))
            return

        if path == "/api/operator/send-conflict-alert":
            self._send_json(executar_alerta_conflito(forcar=True))
            return

        if path == "/api/operator/send-stale-data-alert":
            self._send_json(executar_alerta_dados_antigos(forcar=True))
            return

        self._send_json({"ok": False, "error": "NOT_FOUND"}, status=404)


def iniciar_painel():

    panel = _panel_config()
    host = panel["host"]
    port = panel["port"]
    servidor = ThreadingHTTPServer((host, port), LeonPanelHandler)
    print("===================================")
    print("LEON CONTROL PANEL")
    print("===================================")
    print(f"http://{host}:{port}")
    if host != "127.0.0.1":
        print("REMOTE ACCESS ENABLED")
        print(f"READ ONLY REMOTE: {panel['remote_read_only']}")
    print("===================================")
    servidor.serve_forever()


if __name__ == "__main__":

    iniciar_painel()
