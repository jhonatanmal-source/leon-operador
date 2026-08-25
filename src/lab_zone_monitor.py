"""Monitoramento de zonas de laboratorio (LAB) — promocao por evidencia real.

Este modulo resolve o bloqueio B2 (diagnostico 2026-08-21): zonas criadas por
``create_lab_zone`` nascem em ``AGUARDANDO_ESTRUTURA`` e nunca eram promovidas a
``CONFIRMADA`` porque nenhum processo alimentava evidencia estrutural real ao
``monitor_zone``. Sem promocao, ``validate_zone_for_execution`` bloqueava toda
execucao demo LAB (``REGION_NOT_CONFIRMED``) indefinidamente.

Contrato de seguranca (nao viola nenhuma regra do LEON):
- SOMENTE LEITURA de MT5 (le candles via ``refine_m15_m5``; nunca envia ordem).
- A promocao de status ocorre EXCLUSIVAMENTE dentro de ``monitor_zone`` — este
  modulo nao escreve ``region_status`` diretamente, apenas coleta evidencia real
  de candles e a repassa. Nada de status fabricado.
- ``structural_confirmations`` so e gravado quando a zona ja foi promovida a
  ``CONFIRMADA`` pelo ``monitor_zone``, e reflete os eventos realmente detectados
  (BOS/CHoCH/sweep/gatilho M5), nunca confirmacoes inventadas.
- Nao altera estrategia, risco, TP, SL, conta real ou guards.

Politica de evidencia: CADEIA COMPLETA (igual producao) — liquidez trabalhada +
estrutura confirmada + gatilho M5 (sweep+reclaim+displacement, anti comprar
topo/vender fundo). O gatilho reutiliza ``_micro_trigger`` corrigido em 18/08.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:  # pragma: no cover - fallback de import (padrao do projeto)
    from src.interest_zone_engine import (
        InterestZoneStore,
        TERMINAL_REGION_STATES,
        monitor_zone,
    )
except ImportError:  # pragma: no cover
    from interest_zone_engine import (
        InterestZoneStore,
        TERMINAL_REGION_STATES,
        monitor_zone,
    )

try:  # pragma: no cover
    from src.institutional_analysis_engine import analyze_smc_context
except ImportError:  # pragma: no cover
    from institutional_analysis_engine import analyze_smc_context

try:  # pragma: no cover
    from src.mt5_execution_refiner import _micro_trigger, load_execution_candles
except ImportError:  # pragma: no cover
    from mt5_execution_refiner import _micro_trigger, load_execution_candles


LAB_ZONE_SOURCE = "LABORATORIO"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _pt_direction(region_direction: Any) -> str:
    """Converte direcao canonica (BULLISH/BEARISH) para COMPRA/VENDA."""
    text = str(region_direction or "").strip().upper()
    if text in {"BULLISH", "COMPRA", "BUY"}:
        return "COMPRA"
    if text in {"BEARISH", "VENDA", "SELL"}:
        return "VENDA"
    return ""


def _build_evidence(zone: dict[str, Any], smc: dict[str, Any], trigger: dict[str, Any]) -> dict[str, Any]:
    """Mapeia analise SMC + gatilho M5 real para o contrato de ``monitor_zone``.

    Nao inventa evidencia: cada flag deriva de deteccao real nos candles.
    """
    canon_dir = str(zone.get("region_direction") or "").strip().upper()
    liquidity = dict(smc.get("liquidity") or {})
    liquidity_type = str(liquidity.get("type") or "SEM_EVENTO").upper()
    liquidity_dir = str(liquidity.get("direction") or "").upper()

    liquidity_present = liquidity_type != "SEM_EVENTO"
    # Sweep valido = varredura de liquidez na direcao da zona (contra o extremo
    # oposto). Para zona BULLISH, sweep sell-side (direcao BULLISH); espelho para
    # BEARISH. Alinhamento de direcao confirma que a liquidez foi trabalhada a
    # favor do cenario da zona.
    liquidity_swept = liquidity_present and liquidity_dir == canon_dir

    bos_text = str(smc.get("bos") or "").upper()
    choch_text = str(smc.get("choch") or "").upper()
    bos_present = bool(bos_text) and "SEM_BOS" not in bos_text
    choch_present = bool(choch_text) and "SEM_CHOCH" not in choch_text
    bos_event = dict(smc.get("bos_event") or {})
    displacement_present = bool(bos_event.get("displacement"))

    # Estrutura so conta a favor da direcao da zona.
    structure_dir = str(smc.get("direction") or "").upper()
    structure_aligned = structure_dir == canon_dir
    bos_present = bos_present and structure_aligned
    choch_present = choch_present and structure_aligned

    trigger_confirmed = bool(trigger.get("confirmed"))

    return {
        "liquidity_present": liquidity_present,
        "liquidity_swept": liquidity_swept,
        "bos_present": bos_present,
        "choch_present": choch_present,
        "displacement_present": displacement_present,
        "trigger_confirmed": trigger_confirmed,
    }


def _structural_confirmations(zone: dict[str, Any], smc: dict[str, Any], trigger: dict[str, Any], now_text: str) -> list[dict[str, Any]]:
    """Confirmacoes reais para zona ja promovida a CONFIRMADA por monitor_zone."""
    confirmations: list[dict[str, Any]] = []
    bos_event = dict(smc.get("bos_event") or {})
    liquidity = dict(smc.get("liquidity") or {})

    bos_text = str(smc.get("bos") or "").upper()
    if bos_text and "SEM_BOS" not in bos_text:
        confirmations.append({
            "type": bos_text,
            "source": "institutional_analysis_engine",
            "time": bos_event.get("time") or now_text,
        })
    choch_text = str(smc.get("choch") or "").upper()
    if choch_text and "SEM_CHOCH" not in choch_text:
        confirmations.append({
            "type": choch_text,
            "source": "institutional_analysis_engine",
            "time": now_text,
        })
    liquidity_type = str(liquidity.get("type") or "SEM_EVENTO").upper()
    if liquidity_type != "SEM_EVENTO":
        confirmations.append({
            "type": liquidity_type,
            "source": "institutional_analysis_engine",
            "time": now_text,
        })
    if trigger.get("confirmed"):
        confirmations.append({
            "type": "M5_TRIGGER_SWEEP_RECLAIM",
            "source": "mt5_execution_refiner",
            "time": trigger.get("trigger_time") or now_text,
        })
    return confirmations


def _monitorar_zona(zone: dict[str, Any], store: InterestZoneStore, now: datetime, market: dict[str, Any]) -> dict[str, Any]:
    """Monitora uma unica zona LAB usando candles ja carregados para o simbolo.

    ``market`` e compartilhado entre todas as zonas do mesmo simbolo no ciclo
    (uma unica leitura MT5 por simbolo, nao por zona — evita N inicializacoes
    de MT5 por ciclo quando ha muitas zonas pendentes).
    """
    region_id = str(zone.get("region_id") or "")
    direction_pt = _pt_direction(zone.get("region_direction"))
    previous_status = str(zone.get("region_status") or "")

    if not direction_pt:
        return {"region_id": region_id, "action": "skip", "reason": "ZONA_SEM_DIRECAO"}

    if not market.get("ok"):
        return {
            "region_id": region_id,
            "action": "skip",
            "reason": market.get("error", "MERCADO_INDISPONIVEL"),
        }

    m15 = market.get("m15") or []
    m5 = market.get("m5") or []
    if len(m15) < 20:
        return {"region_id": region_id, "action": "skip", "reason": "INSUFFICIENT_M15"}

    trigger = _micro_trigger(m5, direction_pt) if m5 else {"confirmed": False, "reason": "M5_INDISPONIVEL"}
    smc = analyze_smc_context(m15)
    evidence = _build_evidence(zone, smc, trigger)
    current_price = float(m15[-1]["close"])

    updated = monitor_zone(
        zone,
        current_price=current_price,
        evidence=evidence,
        now=now,
    )
    new_status = str(updated.get("region_status") or "")

    # Confirmacoes reais so quando a zona foi realmente promovida a CONFIRMADA.
    if new_status == "CONFIRMADA":
        confirmations = _structural_confirmations(zone, smc, trigger, now.isoformat(timespec="seconds"))
        updated["structural_confirmations"] = confirmations
        updated["valid_confirmations"] = confirmations

    try:
        store.upsert(updated)
    except Exception as error:  # pragma: no cover - defensivo
        return {"region_id": region_id, "action": "error", "reason": str(error)}

    action = "promoted" if new_status == "CONFIRMADA" and previous_status != "CONFIRMADA" else (
        "invalidated" if new_status == "INVALIDADA" else (
            "expired" if new_status == "EXPIRADA" else "monitored"
        )
    )
    return {
        "region_id": region_id,
        "action": action,
        "from_status": previous_status,
        "to_status": new_status,
    }


def monitorar_zonas_lab(*, store: InterestZoneStore | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Monitora todas as zonas LAB ativas, promovendo por evidencia estrutural real.

    Chamado a cada ciclo de estudo continuo do operador. Faz short-circuit quando
    nao ha zonas de laboratorio, mantendo o custo proximo de zero no caso comum.

    Retorna resumo: ``{ok, monitored, promoted, invalidated, expired, skipped, errors, details}``.
    """
    active_store = store or InterestZoneStore()
    clock = now or _utc_now()

    try:
        all_zones = active_store.list()
    except Exception as error:  # pragma: no cover - defensivo
        return {"ok": False, "error": str(error), "monitored": 0}

    # Escopo B2: apenas zonas LAB ainda na esteira de promocao (nao terminais e
    # ainda nao CONFIRMADA). Zonas ja CONFIRMADA — incluindo artefatos legados
    # anteriores a correcao de 18/08 (pendencia #10), que fabricavam esse
    # status sem evidencia — ficam fora deste loop: (1) evita reprocessar
    # ~1.5k zonas por ciclo (custo de MT5 por zona) e (2) evita efeito
    # colateral fora de escopo de expira-las em massa por idade (>7 dias).
    # Retroatividade sobre as legadas exige decisao dedicada, nao esta missao.
    lab_zones = [
        zone for zone in all_zones
        if str(zone.get("zone_source") or "").upper() == LAB_ZONE_SOURCE
        and str(zone.get("region_status") or "") not in TERMINAL_REGION_STATES
        and str(zone.get("region_status") or "") != "CONFIRMADA"
    ]

    summary: dict[str, Any] = {
        "ok": True,
        "monitored": 0,
        "promoted": 0,
        "invalidated": 0,
        "expired": 0,
        "skipped": 0,
        "errors": 0,
        "details": [],
    }

    if not lab_zones:
        return summary

    # Uma unica leitura MT5 por simbolo no ciclo (nao por zona) — evita reabrir
    # conexao MT5 decenas de vezes quando ha varias zonas do mesmo simbolo.
    zones_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for zone in lab_zones:
        symbol = str(zone.get("symbol") or "").strip()
        if not symbol:
            summary["details"].append({
                "region_id": zone.get("region_id", ""),
                "action": "skip",
                "reason": "ZONA_SEM_SIMBOLO",
            })
            summary["skipped"] += 1
            continue
        zones_by_symbol.setdefault(symbol, []).append(zone)

    market_by_symbol: dict[str, dict[str, Any]] = {}
    for symbol in zones_by_symbol:
        try:
            market_by_symbol[symbol] = load_execution_candles(symbol)
        except Exception as error:  # pragma: no cover - defensivo
            market_by_symbol[symbol] = {"ok": False, "error": str(error)}

    for symbol, zones in zones_by_symbol.items():
        market = market_by_symbol[symbol]
        for zone in zones:
            result = _monitorar_zona(zone, active_store, clock, market)
            summary["details"].append(result)
            action = result.get("action")
            if action == "promoted":
                summary["promoted"] += 1
                summary["monitored"] += 1
            elif action == "invalidated":
                summary["invalidated"] += 1
                summary["monitored"] += 1
            elif action == "expired":
                summary["expired"] += 1
                summary["monitored"] += 1
            elif action == "monitored":
                summary["monitored"] += 1
            elif action == "skip":
                summary["skipped"] += 1
            elif action == "error":
                summary["errors"] += 1

    return summary
