"""
Teste de regressão — Missão 2 (backlog de melhorias de código).

Bug: `_formatar_status()` em `telegram_commands_mcp.py` importava
`detectar_ativo` de `market_reader.py` (módulo que só tem `ler_preco_xau`).
A função real está em `asset_detector.py`. O `except Exception` mascarava
o `ImportError` e o comando `/status` sempre caía no fallback fixo
`Gold_Spot`, mesmo quando a corretora estava usando outro símbolo ativo.

Este teste garante que:
1. O import correto (`asset_detector.detectar_ativo`) não lança exceção.
2. `_formatar_status()` usa o valor retornado por `detectar_ativo()`,
   não o fallback fixo — validado forçando um símbolo diferente via cache.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import src.telegram_commands_mcp as tcm
# Import bare (sem prefixo `src.`) — mesmo caminho usado dentro de
# `_formatar_status()`, que roda com SRC_DIR no sys.path (ver
# telegram_commands_mcp.py, "Path setup"). Precisa ser o mesmo objeto
# de módulo para o monkeypatch surtir efeito no código de produção.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import asset_detector


def test_formatar_status_importa_detectar_ativo_sem_erro():
    """Regressão do bug: import de market_reader (sem detectar_ativo) quebrava e caía no fallback."""
    from asset_detector import detectar_ativo

    # Não deve lançar ImportError/AttributeError.
    ativo = detectar_ativo()
    assert isinstance(ativo, str)
    assert ativo


def test_formatar_status_usa_simbolo_real_nao_fallback_fixo(tmp_path, monkeypatch):
    """
    Garante que o /status reflete o símbolo detectado, e não sempre 'Gold_Spot'
    por causa do except Exception mascarando o import quebrado.
    """
    cache_file = tmp_path / "active_symbol_cache.json"
    cache_file.write_text(
        json.dumps({"ativo": "XAUUSD.fx"}), encoding="utf-8"
    )
    monkeypatch.setattr(asset_detector, "CACHE_FILE", cache_file)
    from src import operational_evidence as evidence
    from datetime import datetime, timezone
    monkeypatch.setattr(evidence, 'DATA', tmp_path)
    (tmp_path / 'operator_heartbeat.json').write_text(json.dumps({
        'updated_at': datetime.now().isoformat(), 'status': 'AGUARDANDO_SETUP', 'details': {}}))
    (tmp_path / 'latest_setup_decision.json').write_text(json.dumps({
        'created_at': datetime.now(timezone.utc).isoformat(), 'plan': {'ativo': 'XAUUSD.fx'}}))

    mensagem = tcm._formatar_status()

    assert "XAUUSD.fx" in mensagem
    assert "`Gold_Spot`" not in mensagem


def test_status_indefinite_requires_fresh_authorized_demo(tmp_path, monkeypatch):
    from datetime import datetime, timedelta
    from src import operational_evidence as evidence
    monkeypatch.setattr(evidence, 'DATA', tmp_path)
    details = dict(execution_authorized=True, scope='demo_execution',
                   autonomy_reason='AUTONOMY_ACTIVE_UNTIL_REVOKED', autonomy_expires_at=None)
    (tmp_path / 'latest_setup_decision.json').write_text(json.dumps({'plan': None}))
    for age, authorized, scope, expected in [
        (0, True, 'demo_execution', True), (600, True, 'demo_execution', False),
        (0, False, 'demo_execution', False), (0, True, 'real_execution', False),
    ]:
        details.update(execution_authorized=authorized, scope=scope)
        (tmp_path / 'operator_heartbeat.json').write_text(json.dumps({
            'updated_at': (datetime.now() - timedelta(seconds=age)).isoformat(),
            'status': 'AGUARDANDO_SETUP', 'details': details}))
        message = evidence.operational_status_text()
        assert ('Ate desligar com /autonomy off' in message) is expected
        assert 'Ativo analisado: Sem registro' in message
        assert 'Autorizacao ate: None' not in message
