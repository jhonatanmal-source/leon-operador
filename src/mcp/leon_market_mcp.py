#!/usr/bin/env python3
"""
Market MCP — LEON XAU ELITE AI
Coleta e organização de dados do mercado. APENAS LEITURA.

SAFETY: Nenhuma função de escrita, ordem, login ou eval é exposta.
Todas as operações passam pelo wrapper _mt5_safe.py que bloqueia:
  - order_send, order_check, login, initialize, shutdown, eval, execute

Tools:
  - check_mt5_status       Verifica disponibilidade do MT5
  - get_current_price      Obtém o preço atual (bid/ask) de um símbolo
  - get_symbol_info        Obtém informações detalhadas de um símbolo
  - get_ohlc               Obtém dados OHLC históricos
  - list_symbols           Lista todos os símbolos disponíveis
  - get_account_info       Obtém informações da conta (read-only)
  - get_market_snapshot    Obtém snapshot completo do mercado
"""

import json
import sys
import os
from pathlib import Path

# Add project root, src, and mcp directory to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_MCP_DIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, _MCP_DIR)
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_protocol import MCPBaseHandler, MCPError, INVALID_PARAMS, run_server
from asset_detector import detectar_ativo
from mt5_safe import (
    check_mt5,
    safe_symbol_info_tick,
    safe_symbol_info,
    safe_symbols_get,
    safe_copy_rates_from_pos,
    safe_account_info,
)


def _mt5_disponivel() -> bool:
    """Consulta disponibilidade REAL do MT5 (dispara _ensure_initialized()).

    IMPORTANTE: NÃO usar `from mt5_safe import _MT5_AVAILABLE` — isso copia
    o valor `False` no import e a flag nunca é atualizada neste módulo.
    `check_mt5()` retorna o status atual e força a inicialização lazy.
    """
    status = check_mt5()
    return bool(status.get("available", False))


class MarketMCPHandler(MCPBaseHandler):
    def __init__(self, *args, **kwargs):
        super().__init__("leon-market-mcp", "1.0.0")

    def register_tools(self):
        # 1. check_mt5_status
        self.add_tool_def(
            name="check_mt5_status",
            description="Verifica se o módulo MT5 está disponível e acessível.",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self.handle_check_mt5_status
        )

        # 2. get_current_price
        self.add_tool_def(
            name="get_current_price",
            description="Obtém o preço atual (bid/ask) de um símbolo no MT5.",
            input_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Símbolo do ativo (ex: XAUUSD, EURUSD, BTCUSD)"
                    }
                },
                "required": ["symbol"]
            },
            handler=self.handle_get_current_price
        )

        # 3. get_symbol_info
        self.add_tool_def(
            name="get_symbol_info",
            description="Obtém informações detalhadas de um símbolo (digitos, spread, volume, etc).",
            input_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Símbolo do ativo"
                    }
                },
                "required": ["symbol"]
            },
            handler=self.handle_get_symbol_info
        )

        # 4. get_ohlc
        self.add_tool_def(
            name="get_ohlc",
            description="Obtém dados OHLC (Open, High, Low, Close) históricos para um símbolo.",
            input_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Símbolo do ativo (ex: XAUUSD)"
                    },
                    "timeframe": {
                        "type": "integer",
                        "description": "Timeframe em minutos (1=1min, 5=5min, 15=15min, 60=1h, 240=4h, 1440=1d). Default: 15",
                        "default": 15
                    },
                    "count": {
                        "type": "integer",
                        "description": "Número de candles. Default: 20",
                        "default": 20
                    }
                },
                "required": ["symbol"]
            },
            handler=self.handle_get_ohlc
        )

        # 5. list_symbols
        self.add_tool_def(
            name="list_symbols",
            description="Lista todos os símbolos disponíveis no MT5.",
            input_schema={
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "description": "Filtro opcional para buscar símbolos (ex: XAU, EUR, BTC)",
                        "default": ""
                    }
                },
                "required": []
            },
            handler=self.handle_list_symbols
        )

        # 6. get_account_info
        self.add_tool_def(
            name="get_account_info",
            description="Obtém informações da conta MT5 (saldo, equity, margem, alavancagem). Apenas leitura.",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self.handle_get_account_info
        )

        # 7. get_market_snapshot
        self.add_tool_def(
            name="get_market_snapshot",
            description="Obtém um snapshot completo do mercado: preços atuais, OHLC e informações de múltiplos símbolos.",
            input_schema={
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de símbolos para o snapshot. Se vazio, detecta automaticamente o símbolo ativo da corretora.",
                        "default": []
                    }
                },
                "required": []
            },
            handler=self.handle_get_market_snapshot
        )

    # --- Tool handlers ---

    def handle_check_mt5_status(self) -> dict:
        return check_mt5()

    def handle_get_current_price(self, symbol: str) -> dict:
        if not _mt5_disponivel():
            return {"error": "MT5 não disponível", "symbol": symbol}
        return safe_symbol_info_tick(symbol)

    def handle_get_symbol_info(self, symbol: str) -> dict:
        if not _mt5_disponivel():
            return {"error": "MT5 não disponível", "symbol": symbol}
        return safe_symbol_info(symbol)

    def handle_get_ohlc(self, symbol: str, timeframe: int = 15, count: int = 20) -> dict:
        if not _mt5_disponivel():
            return {"error": "MT5 não disponível", "symbol": symbol}
        
        # Convert timeframe minutes to MT5 constant
        tf_map = {
            1: 1,       # PERIOD_M1
            5: 5,       # PERIOD_M5
            15: 15,     # PERIOD_M15
            30: 30,     # PERIOD_M30
            60: 60,     # PERIOD_H1
            120: 120,   # PERIOD_H2
            240: 240,   # PERIOD_H4
            360: 360,   # PERIOD_H6
            720: 720,   # PERIOD_H12
            1440: 1440, # PERIOD_D1
            10080: 10080, # PERIOD_W1
            43200: 43200, # PERIOD_MN1
        }
        
        mt5_tf = tf_map.get(timeframe, 15)
        return safe_copy_rates_from_pos(symbol, mt5_tf, 0, count)

    def handle_list_symbols(self, filter: str = "") -> dict:
        if not _mt5_disponivel():
            return {"error": "MT5 não disponível"}
        
        result = safe_symbols_get()
        if "error" in result:
            return result
        
        if filter:
            filter_upper = filter.upper()
            filtered = [s for s in result.get("symbols", []) if filter_upper in s.get("name", "").upper()]
            return {"symbols": filtered, "count": len(filtered), "filter": filter}
        
        return result

    def handle_get_account_info(self) -> dict:
        if not _mt5_disponivel():
            return {"error": "MT5 não disponível"}
        return safe_account_info()

    def handle_get_market_snapshot(self, symbols: list = None) -> dict:
        if symbols is None or len(symbols) == 0:
            ativo = detectar_ativo()
            symbols = [ativo]
        
        if not _mt5_disponivel():
            return {"error": "MT5 não disponível", "symbols": symbols}
        
        snapshot = {}
        for sym in symbols:
            price = safe_symbol_info_tick(sym)
            info = safe_symbol_info(sym)
            ohlc = safe_copy_rates_from_pos(sym, 15, 0, 5)  # 5 candles M15
            
            snapshot[sym] = {
                "price": price if "error" not in price else None,
                "info": info if "error" not in info else None,
                "ohlc_m15_last_5": ohlc if "error" not in ohlc else None
            }
        
        # Get account overview once
        account = safe_account_info()
        
        return {
            "symbols": symbols,
            "timestamp": str(__import__("datetime").datetime.now()),
            "snapshot": snapshot,
            "account": account if "error" not in account else None
        }


if __name__ == "__main__":
    run_server(MarketMCPHandler, "leon-market-mcp", "1.0.0")
