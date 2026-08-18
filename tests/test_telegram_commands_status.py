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

    mensagem = tcm._formatar_status()

    assert "XAUUSD.fx" in mensagem
    assert "`Gold_Spot`" not in mensagem
