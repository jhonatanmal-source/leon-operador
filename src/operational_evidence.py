"""Setup evidence and confirmed MT5 outcomes; no order execution."""

import json
import math
import os
import tempfile
import sqlite3
import hashlib
from statistics import median, stdev
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
VERSION = "elliott-multidegree-smc-entry-v2.8"


def read_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".evidence-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(value, file, ensure_ascii=False, indent=2, allow_nan=False)
            file.flush()
            os.fsync(file.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def select_elliott_entry(h1, m15, direction, h1_bias):
    """Prefer the existing H1 entry; permit a confirmed M15 degree, not a fallback count."""
    expected = {"COMPRA": "ALTA", "VENDA": "BAIXA"}.get(direction)
    def eligible(context):
        return (expected is not None and context.get("valid") is True
                and context.get("entry_eligible") is True
                and context.get("direction") == expected)
    if eligible(h1):
        return dict(h1, entry_timeframe="H1", selection_reason="H1_ENTRY_ELIGIBLE")
    if eligible(m15) and h1_bias in (expected, "LATERAL"):
        return dict(m15, entry_timeframe="M15", selection_reason="M15_ENTRY_H1_NOT_OPPOSING")
    # Do not return an otherwise eligible H1 count with an opposing direction.
    return dict(h1, entry_eligible=False, entry_timeframe="H1",
                selection_reason="NO_ALIGNED_ELLIOTT_ENTRY")


def select_elliott_direction(h1, m15, h1_bias, top_down=None):
    """Select context before the SMC decision, never by matching its candidate."""
    context, timeframe = (h1, 'H1') if h1_bias in ('ALTA', 'BAIXA') else (m15, 'M15')
    selected = dict(context, role='DIRECTION_ONLY', entry_timeframe=timeframe,
                    selection_reason='DIRECTION_CONTEXT_NOT_ENTRY_TRIGGER')
    if top_down is not None:
        from src.multidegree_context import describe_multidegree
        degrees = describe_multidegree(top_down)
        macro = degrees['macro_direction']
        allowed = [macro] if macro in ('ALTA', 'BAIXA') else []
        for correction in degrees['corrections']:
            if correction['direction'] not in allowed:
                allowed.append(correction['direction'])
        selected.update(role='MULTIDEGREE_DIRECTION', degrees=degrees,
                        allowed_directions=allowed,
                        selection_reason='MACRO_AND_CORRECTION_DISTINCT_SMC_TRIGGERS')
    return selected


def elliott_direction_allows(elliott, direction):
    expected = {'COMPRA': 'ALTA', 'VENDA': 'BAIXA'}.get(direction)
    if elliott.get('role') == 'MULTIDEGREE_DIRECTION':
        return expected is not None and expected in elliott.get('allowed_directions', [])
    if expected is None or elliott.get('direction') != expected:
        return False
    if elliott.get('role') == 'DIRECTION_ONLY':
        return True
    return elliott.get('valid') is True and elliott.get('entry_eligible') is True


def wave_liquidity_confirmation(direction, elliott, smc, structural_zone=None):
    """Use the analyzer's entry contract for every supported Elliott family."""
    expected = {"COMPRA": "ALTA", "VENDA": "BAIXA"}.get(direction)
    smc_direction = {"COMPRA": "BULLISH", "VENDA": "BEARISH"}.get(direction)
    liquidity = smc.get("liquidity") or {}
    wave_ok = elliott_direction_allows(elliott, direction)
    liquidity_ok = (smc_direction is not None
                    and smc.get("direction") == smc_direction
                    and liquidity.get("direction") == smc_direction
                    and liquidity.get("index") is not None
                    and not smc.get("liquidity_conflict"))
    zone = structural_zone or {}
    structural_ok = (smc_direction is not None and zone.get('zone_source') == 'REAL_M15_OB_V1'
                     and zone.get('region_direction') == smc_direction
                     and zone.get('region_status') == 'CONFIRMADA' and zone.get('region_valid') is True
                     and not zone.get('region_invalidated') and bool(zone.get('structural_confirmations')))
    missing = []
    if not wave_ok:
        missing.append("DIRECTION_CONTEXT_MISSING_OR_OPPOSING" if elliott.get('role') in ('DIRECTION_ONLY', 'MULTIDEGREE_DIRECTION')
                       else "ELLIOTT_ENTRY_NOT_ELIGIBLE_OR_DIRECTION_MISMATCH")
    if not liquidity_ok and not structural_ok:
        missing.append("LIQUIDITY_MISSING_OR_CONFLICTING")
    return {"approved": wave_ok and (liquidity_ok or structural_ok), "wave_eligible": wave_ok,
            "structural_zone_confirmed": structural_ok,
            "liquidity_aligned": liquidity_ok, "missing": missing,
            "liquidity": liquidity, "elliott_label": elliott.get("label")}


def setup_decision(direction, elliott, smc_approved, wave_confirmed, top_down_approved):
    checks = {
        "direction": direction in ("COMPRA", "VENDA"),
        "elliott": elliott_direction_allows(elliott, direction),
        "smc": smc_approved is True,
        "wave_liquidity": wave_confirmed is True,
        "top_down": top_down_approved is True,
    }
    missing = [name for name, passed in checks.items() if not passed]
    return {"approved": not missing, "checks": checks, "missing": missing,
            "stage": "TRIGGER_CONFIRMED" if not missing else "WAITING_CONFIRMATION",
            "entry_reason": ('SETUP_READY' if not missing else
                             'ELLIOTT_CONTEXT_ONLY' if elliott.get('role') not in ('DIRECTION_ONLY', 'MULTIDEGREE_DIRECTION') and elliott.get('valid') and not elliott.get('entry_eligible') else
                             'MISSING_' + '_'.join(missing)),
            "version": VERSION, "elliott": elliott}


def record_setup_funnel(preop, proof):
    """Count decisions, not trades. A pre-operation is counted once per version."""
    day = proof['created_at'][:10]
    DATA.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATA / 'setup_funnel.sqlite3', timeout=5) as db:
        db.execute('CREATE TABLE IF NOT EXISTS decisions (id TEXT, version TEXT, day TEXT, approved INTEGER, missing TEXT, PRIMARY KEY(id,version))')
        db.execute('CREATE INDEX IF NOT EXISTS decisions_day ON decisions(day,version)')
        db.execute('INSERT OR IGNORE INTO decisions VALUES(?,?,?,?,?)',
                   (preop['id'], VERSION, day, int(proof['approved']), json.dumps(proof['missing'])))
        rows = db.execute('SELECT approved,missing FROM decisions WHERE day=? AND version=?', (day, VERSION)).fetchall()
    reasons = {}
    for _, missing in rows:
        for reason in json.loads(missing):
            reasons[reason] = reasons.get(reason, 0) + 1
    return {'day': day, 'timezone': 'UTC', 'version': VERSION, 'candidates': len(rows),
            'approved': sum(row[0] for row in rows), 'blocked_by': reasons}


def save_setup_evidence(preop, decision):
    proof = dict(decision)
    proof.update({"pre_operation_id": preop["id"], "created_at": datetime.now(timezone.utc).isoformat(),
                  "plan": {key: str(preop.get(key, "")) for key in ("ativo", "direcao", "entrada", "stop", "tp2")}})
    structure = {'asset': proof['plan']['ativo'], 'direction': proof['plan']['direcao'],
                 'label': proof['elliott'].get('label'),
                 'pivots': [{k: p.get(k) for k in ('type', 'price', 'time')}
                            for p in proof['elliott'].get('pivots', [])[-6:]]}
    proof['structure_id'] = hashlib.sha256(json.dumps(structure, sort_keys=True, allow_nan=False).encode()).hexdigest()
    proof["approved"] = bool(proof["approved"] and preop.get("status") == "ABERTO")
    if not proof['approved'] and not proof['missing']:
        proof['missing'] = ['pre_operation_not_open']
    proof['stage'] = 'ENTRY_READY' if proof['approved'] else 'WAITING_CONFIRMATION'
    try:
        proof['funnel'] = record_setup_funnel(preop, proof)
    except (OSError, sqlite3.Error):
        proof['telemetry_error'] = True
    atomic_json(DATA / "setup_evidence" / (preop["id"] + ".json"), proof)
    atomic_json(DATA / "latest_setup_decision.json", proof)
    return proof


def validate_setup_evidence(preop, now=None):
    identifier = str(preop.get("id", ""))
    if not identifier or Path(identifier).name != identifier:
        return {"ok": False, "error": "SETUP_EVIDENCE_MISSING"}
    try:
        proof = read_json(DATA / "setup_evidence" / (identifier + ".json"), {})
        if proof.get("version") != VERSION or not proof.get("approved"):
            return {"ok": False, "error": "SETUP_NOT_CONFIRMED", "missing": proof.get("missing", [])}
        latest = read_json(DATA / "latest_setup_decision.json", {})
        if (latest.get('version') != VERSION or not latest.get("approved")
                or latest.get('structure_id') != proof.get('structure_id')
                or latest.get('plan', {}).get('ativo') != proof['plan'].get('ativo')
                or latest.get("plan", {}).get("direcao") != proof["plan"].get("direcao")
                or latest.get("elliott", {}).get("label") != proof.get("elliott", {}).get("label")):
            return {"ok": False, "error": "LATEST_SETUP_NOT_CONFIRMED"}
        age = ((now or datetime.now(timezone.utc)) - datetime.fromisoformat(proof["created_at"])).total_seconds()
        if age < 0 or age > 180:
            return {"ok": False, "error": "SETUP_EVIDENCE_STALE"}
        for key, value in proof["plan"].items():
            if str(preop.get(key, "")) != value:
                return {"ok": False, "error": "SETUP_PLAN_CHANGED"}
        return {"ok": True, "proof": proof}
    except (OSError, ValueError, KeyError, TypeError):
        return {"ok": False, "error": "SETUP_EVIDENCE_INVALID"}


def confirmed_records():
    records = read_json(DATA / "confirmed_mt5_outcomes.json", {})
    return list(records.values())


def record_confirmed_outcome(operation):
    import fcntl
    if operation.get("source") != "MT5_DEMO_REAL" or not operation.get("position_id") or not operation.get("account_key"):
        raise ValueError("Confirmed MT5 identity required")
    if not math.isfinite(float(operation["actual_profit"])):
        raise ValueError("Invalid net profit")
    key = f"{operation['account_key']}:{operation['position_id']}"
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / "confirmed_mt5_outcomes.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = DATA / "confirmed_mt5_outcomes.json"
        records = read_json(path, {})
        is_new = key not in records
        records[key] = operation
        atomic_json(path, records)
    return is_new


def pattern_key(operation):
    base = [str(operation.get(key, "")) for key in ("ativo", "direcao", "smc", "elliott")]
    # Legacy outcomes stay identifiable; never infer a model from their result.
    return "|".join(base + [str(operation.get(key) or "UNSPECIFIED")
                            for key in ("entry_model", "context_mode")])


def learning_statistics(preop):
    from src.opportunity_learning import opportunity_statistics
    return opportunity_statistics(preop, confirmed_records(), VERSION)


def learning_score(preop):
    return learning_statistics(preop)['selection_score']


def daily_evidence_report(day):
    from src.opportunity_learning import learning_summary
    rows = [r for r in confirmed_records() if r.get('source') == 'MT5_DEMO_REAL'
            and str(r.get("data_fechamento", ""))[:10] <= str(day)]
    learning = learning_summary(rows, VERSION)
    groups = {}
    for row in rows:
        key = pattern_key(row) + "|" + row.get("setup_version", "LEGACY") + "|" + row.get("currency", "UNKNOWN")
        group = groups.setdefault(key, {"samples": 0, "wins": 0, "losses": 0, "net_profit": 0.0, "tickets": []})
        pnl = float(row["actual_profit"])
        group["samples"] += 1
        group["wins"] += pnl > 0
        group["losses"] += pnl < 0
        group["net_profit"] = round(group["net_profit"] + pnl, 2)
        group["tickets"].append(f"{row['account_key']}:{row['position_id']}")
    snapshot = {"date": str(day), "version": VERSION, "confirmed_positions": len(rows), "patterns": groups,
                "learning": learning,
                "rule": "Exploratory SMC/context ranking; mean ticket R per account/region, minimum 4 independent opportunities; shrink n/(n+20). Not validated edge. No risk, SL or TP changes.",
                "changes": "Evidence updated; risk limits and setup requirements unchanged."}
    snapshot["subsequent_outcomes"] = [
        {"ticket": r["position_id"], "account": r["account_key"], "score_at_entry": r.get("selection_score_at_entry"),
         "realized_r": r.get("realized_r"), "closed_at": r.get("data_fechamento")}
        for r in rows if r.get("setup_version") == VERSION
    ]
    atomic_json(DATA / "learning_snapshots" / (str(day) + "-confirmed.json"), snapshot)
    vault = DATA.parent / "obsidian_vault" / "aprendizados_diarios"
    vault.mkdir(parents=True, exist_ok=True)
    lines = [f"# Evidencias confirmadas - {day}", "", f"Versao: {VERSION}",
             f"Posicoes fechadas confirmadas: {len(rows)}", "",
             "Observacoes e simulacoes nao entram nesta estatistica.",
             f"Oportunidades independentes da versao atual: {learning['independent_opportunities']}",
             f"Escolhas alteradas pelo ranking entre fechamentos rastreados: {learning['selection_attribution']['changed_choice']}",
             "Ranking por modelo SMC e contexto; minimo de 4 oportunidades independentes por grupo.",
             "Retorno medio dos tickets por regiao; nao e retorno da conta. Vantagem ainda nao validada.",
             "Risco, stop e alvo nao sao alterados pelo aprendizado.", ""]
    for key, group in groups.items():
        lines.extend([f"## {key}", f"Tickets (nao oportunidades): {group['samples']}; ganhos: {group['wins']}; perdas: {group['losses']}",
                      "Tickets: " + ", ".join(group["tickets"]), ""])
    lines.append('## Aprendizado por oportunidade')
    for key, group in learning['groups'].items():
        lines.append(f"- {key}: {group['samples']} oportunidades; {group['trade_count']} tickets; prioridade {group['selection_score']:.4f}; {group['status']}")
    lines.append("## Decisao registrada e resultado posterior")
    for row in snapshot["subsequent_outcomes"]:
        lines.append(f"- {row['account']}:{row['ticket']}: prioridade na entrada {row['score_at_entry']}; resultado {row['realized_r']} R")
    (vault / (str(day) + "-evidencias.md")).write_text("\n".join(lines), encoding="utf-8")
    return snapshot


def operational_status_text():
    try:
        heartbeat = read_json(DATA / "operator_heartbeat.json", {})
        rows = confirmed_records()
        updated = datetime.fromisoformat(heartbeat.get("updated_at", ""))
        stale = (datetime.now() - updated).total_seconds() > 180
        details = heartbeat.get("details", {})
        status = "SEM_ATUALIZACAO" if stale else heartbeat.get("status", "SEM_DADOS")
        state_labels = {"AGUARDANDO_SETUP": "Aguardando setup", "PAUSA_RISCO": "Pausa por risco",
                        "FALHA_TECNICA": "Falha tecnica", "OBSERVACAO": "Sem autorizacao de execucao",
                        "ORDEM_ENVIADA": "Ordem enviada", "SEM_ATUALIZACAO": "Sem atualizacao recente"}
        check_labels = {"elliott": "direcao do contexto", "smc": "confirmacao SMC",
                        "wave_liquidity": "onda e liquidez", "top_down": "alinhamento dos tempos", "direction": "direcao"}
        missing = [check_labels.get(key, key) for key, passed in details.get("setup_checks", {}).items() if not passed]
        reason = details.get("entry_reason", "Sem diagnostico recente")
        if status == "AGUARDANDO_SETUP":
            reason = "Faltam: " + ", ".join(missing) if missing else "Aguardando gatilho de entrada confirmado"
            proof = read_json(DATA / 'latest_setup_decision.json', {})
            trace = proof.get('entry_diagnostics') or {}
            if not missing and proof.get('version') == VERSION and trace.get('reason'):
                reason = 'Calculo de entrada: ' + str(trace['reason'])
                if trace.get('structural_reason'):
                    reason += '; zona SMC: ' + str(trace['structural_reason'])[:350]
        current = [r for r in rows if r.get("setup_version") == VERSION]
        from src.opportunity_learning import learning_summary
        learning = learning_summary(rows, VERSION)
        last_selection = read_json(DATA / 'latest_learning_selection.json', {})
        learning_choice = ('alterou a escolha' if last_selection.get('changed_choice') else 'manteve a escolha') if last_selection else 'ainda sem comparacao registrada'
        wins = sum(float(r["actual_profit"]) > 0 for r in current)
        losses = sum(float(r["actual_profit"]) < 0 for r in current)
        return "\n".join([
            "LEON | Estado do operador", f"Estado: {state_labels.get(status, status)}",
            f"Motivo: {reason}",
            f"Atualizado: {heartbeat.get('updated_at')}", "",
            f"Autorizacao ate: {details.get('autonomy_expires_at', 'Consultar /autonomy')}", "",
            "Elliott + SMC | versao atual",
            f"Posicoes fechadas confirmadas: {len(current)}",
            f"Ganhos: {wins} | Perdas: {losses} | Zero: {len(current) - wins - losses}",
            f"Historico anterior separado: {len(rows) - len(current)}",
            "Aprendizado: ranking por resultado confirmado; sem mudar risco, stop ou alvo.",
            f"Oportunidades independentes: {learning['independent_opportunities']} | Grupos SMC: {len(learning['groups'])}",
            f"Ultima selecao: {learning_choice}. Vantagem ainda nao validada.",
            "Risco por entrada: 0,5% | Maximo aberto: 3 posicoes",
            "Parada diaria: 2% | Devolucao: 50% do lucro de posicoes fechadas",
            "Quantidade diaria de entradas: sem limite",
        ])
    except (OSError, ValueError, KeyError, TypeError):
        return "LEON | Estado indisponivel. Falha ao ler os registros operacionais."
