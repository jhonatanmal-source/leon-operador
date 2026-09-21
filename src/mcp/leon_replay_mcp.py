#!/usr/bin/env python3
"""
Replay MCP — LEON XAU ELITE AI
Reprodução e análise de operações passadas.

Tools:
  - list_operations           Lista operações registradas no shadow_trade
  - get_operation_detail      Detalha uma operação específica
  - analyze_operation         Analisa o resultado de uma operação
  - list_replays              Lista replays disponíveis
  - replay_operation          Reproduz uma operação passo a passo
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add project root and mcp directory to path
_CURR_DIR = Path(__file__).resolve()
sys.path.insert(0, str(_CURR_DIR.parent))         # src/mcp
sys.path.insert(0, str(_CURR_DIR.parent.parent))   # src
sys.path.insert(0, str(_CURR_DIR.parent.parent.parent))  # project root

from mcp_protocol import MCPBaseHandler, MCPError, INVALID_PARAMS, run_server

# Import shadow_trade
try:
    import shadow_trade
    SHADOW_AVAILABLE = True
except ImportError:
    SHADOW_AVAILABLE = False

# Find CSV files for trades
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SHADOW_FILE = PROJECT_ROOT / "data" / "shadow_trades.csv"

# Look for other trade data files
REPLAY_DIR = PROJECT_ROOT / "data" / "replays"


class ReplayMCPHandler(MCPBaseHandler):
    def __init__(self, *args, **kwargs):
        super().__init__("leon-replay-mcp", "1.0.0")

    def register_tools(self):
        # 1. list_operations
        self.add_tool_def(
            name="list_operations",
            description="Lista todas as operações registradas no shadow_trade, com opção de filtro por data ou status.",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filtrar por status (open, closed, all). Default: all",
                        "default": "all"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Número máximo de resultados. Default: 20",
                        "default": 20
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Filtrar por dias atrás. Default: 30",
                        "default": 30
                    }
                },
                "required": []
            },
            handler=self.handle_list_operations
        )

        # 2. get_operation_detail
        self.add_tool_def(
            name="get_operation_detail",
            description="Obtém detalhes completos de uma operação específica pelo ID.",
            input_schema={
                "type": "object",
                "properties": {
                    "operation_id": {
                        "type": "string",
                        "description": "ID da operação (ex: SHADOW-000001)"
                    }
                },
                "required": ["operation_id"]
            },
            handler=self.handle_get_operation_detail
        )

        # 3. analyze_operation
        self.add_tool_def(
            name="analyze_operation",
            description="Analisa o resultado de uma operação, calculando métricas de performance.",
            input_schema={
                "type": "object",
                "properties": {
                    "operation_id": {
                        "type": "string",
                        "description": "ID da operação para análise"
                    }
                },
                "required": ["operation_id"]
            },
            handler=self.handle_analyze_operation
        )

        # 4. list_replays
        self.add_tool_def(
            name="list_replays",
            description="Lista replays disponíveis (arquivos de reprodução de operações passadas).",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Número máximo de resultados. Default: 10",
                        "default": 10
                    }
                },
                "required": []
            },
            handler=self.handle_list_replays
        )

        # 5. replay_operation
        self.add_tool_def(
            name="replay_operation",
            description="Reproduz uma operação passo a passo, mostrando candles, entradas, stops e targets.",
            input_schema={
                "type": "object",
                "properties": {
                    "operation_id": {
                        "type": "string",
                        "description": "ID da operação para reproduzir"
                    },
                    "step_by_step": {
                        "type": "boolean",
                        "description": "Se true, mostra passo a passo. Se false, mostra resumo. Default: true",
                        "default": True
                    }
                },
                "required": ["operation_id"]
            },
            handler=self.handle_replay_operation
        )

    # --- Data loading ---

    def _load_operations(self) -> list:
        """Load operations from shadow_trades.csv"""
        if not SHADOW_FILE.exists():
            return []
        
        import csv
        try:
            with open(SHADOW_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                return list(reader)
        except Exception:
            return []

    def _find_operation(self, operation_id: str) -> dict | None:
        """Find a specific operation by ID."""
        ops = self._load_operations()
        for op in ops:
            if op.get("id") == operation_id:
                return op
        return None

    # --- Tool handlers ---

    def handle_list_operations(self, status: str = "all", limit: int = 20, days_back: int = 30) -> dict:
        if not SHADOW_AVAILABLE:
            return {"error": "shadow_trade module not available", "operations": [], "count": 0}
        
        ops = self._load_operations()
        
        # Filter by status
        if status != "all":
            ops = [op for op in ops if op.get("status", "").lower() == status.lower()]
        
        # Filter by days_back
        if days_back > 0:
            cutoff = datetime.now() - timedelta(days=days_back)
            filtered = []
            for op in ops:
                try:
                    op_date = datetime.strptime(op.get("opened_at", ""), "%Y-%m-%d %H:%M:%S")
                    if op_date >= cutoff:
                        filtered.append(op)
                except (ValueError, TypeError):
                    filtered.append(op)
            ops = filtered
        
        # Limit
        ops = ops[:limit]
        
        # Return summary
        result = []
        for op in ops:
            result.append({
                "id": op.get("id", "N/A"),
                "symbol": op.get("symbol", "N/A"),
                "direction": op.get("direction", "N/A"),
                "entry": op.get("entry", "N/A"),
                "status": op.get("status", "N/A"),
                "result": op.get("result", "N/A"),
                "opened_at": op.get("opened_at", "N/A"),
                "closed_at": op.get("closed_at", "N/A"),
            })
        
        return {
            "total": len(result),
            "filter": {"status": status, "days_back": days_back},
            "operations": result
        }

    def handle_get_operation_detail(self, operation_id: str) -> dict:
        op = self._find_operation(operation_id)
        if not op:
            return {"error": f"Operation '{operation_id}' not found"}
        
        return {
            "operation": op,
            "analysis": self._calculate_metrics(op)
        }

    def handle_analyze_operation(self, operation_id: str) -> dict:
        op = self._find_operation(operation_id)
        if not op:
            return {"error": f"Operation '{operation_id}' not found"}
        
        metrics = self._calculate_metrics(op)
        
        # Generate judgment
        judgment = self._judge_operation(op, metrics)
        
        return {
            "operation_id": operation_id,
            "metrics": metrics,
            "judgment": judgment
        }

    def handle_list_replays(self, limit: int = 10) -> dict:
        """List available replay files."""
        replays = []
        
        # Check shadow_trades.csv
        if SHADOW_FILE.exists():
            ops = self._load_operations()
            for op in ops[:limit]:
                replays.append({
                    "id": op.get("id", "N/A"),
                    "type": "shadow_trade",
                    "symbol": op.get("symbol", "N/A"),
                    "direction": op.get("direction", "N/A"),
                    "date": op.get("opened_at", "N/A"),
                    "status": op.get("status", "N/A")
                })
        
        # Check replay directory
        if REPLAY_DIR.exists():
            for f in sorted(REPLAY_DIR.iterdir())[:limit]:
                if f.suffix in (".json", ".csv", ".md"):
                    replays.append({
                        "id": f.stem,
                        "type": "replay_file",
                        "file": str(f.name),
                        "size": f.stat().st_size
                    })
        
        return {
            "total": len(replays),
            "replays": replays[:limit]
        }

    def handle_replay_operation(self, operation_id: str, step_by_step: bool = True) -> dict:
        op = self._find_operation(operation_id)
        if not op:
            return {"error": f"Operation '{operation_id}' not found"}
        
        # Build replay data
        replay = {
            "operation_id": operation_id,
            "symbol": op.get("symbol", "N/A"),
            "direction": op.get("direction", "N/A"),
            "entry": op.get("entry", "N/A"),
            "stop": op.get("stop", "N/A"),
            "target": op.get("target", "N/A"),
            "opened_at": op.get("opened_at", "N/A"),
            "closed_at": op.get("closed_at", "N/A"),
            "status": op.get("status", "N/A"),
            "result": op.get("result", "N/A"),
            "missing_confirmations": op.get("missing_confirmations", "N/A"),
            "event_signature": op.get("event_signature", "N/A"),
        }
        
        # If step-by-step, add walkthrough
        if step_by_step:
            walkthrough = self._generate_walkthrough(op)
            replay["step_by_step"] = walkthrough
        
        return {
            "replay": replay,
            "step_by_step": step_by_step
        }

    # --- Helper methods ---

    def _calculate_metrics(self, op: dict) -> dict:
        """Calculate performance metrics for an operation."""
        metrics = {
            "has_entry": False,
            "has_stop": False,
            "has_target": False,
            "risk_reward": None,
            "result_points": None,
            "result_percent": None,
            "duration_minutes": None
        }
        
        try:
            entry = float(op.get("entry", 0))
            stop = float(op.get("stop", 0))
            target = float(op.get("target", 0))
            
            if entry and stop:
                metrics["has_entry"] = True
                metrics["has_stop"] = True
                risk = abs(entry - stop)
                metrics["risk_points"] = round(risk, 2)
            
            if entry and target:
                metrics["has_target"] = True
                reward = abs(target - entry)
                metrics["reward_points"] = round(reward, 2)
            
            if metrics.get("risk_points") and metrics.get("reward_points"):
                if metrics["risk_points"] > 0:
                    metrics["risk_reward"] = round(metrics["reward_points"] / metrics["risk_points"], 2)
            
            # Calculate result
            result_str = op.get("result", "")
            if result_str and result_str not in ("N/A", ""):
                try:
                    metrics["result_points"] = float(result_str)
                except ValueError:
                    metrics["result_text"] = result_str
            
            # Duration
            opened = op.get("opened_at", "")
            closed = op.get("closed_at", "")
            if opened and closed:
                try:
                    opened_dt = datetime.strptime(opened, "%Y-%m-%d %H:%M:%S")
                    closed_dt = datetime.strptime(closed, "%Y-%m-%d %H:%M:%S")
                    duration = (closed_dt - opened_dt).total_seconds() / 60
                    metrics["duration_minutes"] = round(duration)
                except (ValueError, TypeError):
                    pass
        
        except (ValueError, TypeError, ZeroDivisionError):
            pass
        
        return metrics

    def _judge_operation(self, op: dict, metrics: dict) -> dict:
        """Generate a judgment for the operation."""
        result = op.get("result", "")
        
        if result and result not in ("N/A", ""):
            try:
                result_float = float(result)
                if result_float > 0:
                    return {"verdict": "ACERTO", "reason": "Trade lucrativo", "score": 80}
                elif result_float < 0:
                    return {"verdict": "ERRO", "reason": "Trade com prejuízo", "score": 30}
                else:
                    return {"verdict": "EMPATE", "reason": "Trade no zero a zero", "score": 50}
            except ValueError:
                pass
        
        # Fallback
        rr = metrics.get("risk_reward")
        if rr and rr >= 2:
            return {"verdict": "POTENCIAL ACERTO", "reason": f"RR favorável: {rr}", "score": 70}
        elif rr and rr >= 1:
            return {"verdict": "NEUTRO", "reason": f"RR equilibrado: {rr}", "score": 50}
        
        return {"verdict": "SEM DADOS", "reason": "Resultado não disponível para julgamento", "score": 0}

    def _generate_walkthrough(self, op: dict) -> list:
        """Generate a step-by-step walkthrough of the operation."""
        steps = []
        
        # Step 1: Setup
        steps.append({
            "step": 1,
            "action": "Setup identificado",
            "detail": f"{op.get('direction', 'N/A')} em {op.get('symbol', 'N/A')}",
            "timestamp": op.get("opened_at", "N/A")
        })
        
        # Step 2: Entry
        steps.append({
            "step": 2,
            "action": "Entrada executada",
            "detail": f"Preço de entrada: {op.get('entry', 'N/A')}",
            "timestamp": op.get("opened_at", "N/A")
        })
        
        # Step 3: Stop Loss
        steps.append({
            "step": 3,
            "action": "Stop Loss definido",
            "detail": f"SL em {op.get('stop', 'N/A')}",
        })
        
        # Step 4: Take Profit
        steps.append({
            "step": 4,
            "action": "Take Profit definido",
            "detail": f"TP em {op.get('target', 'N/A')}",
        })
        
        # Step 5: Missing confirmations
        mc = op.get("missing_confirmations", "")
        steps.append({
            "step": 5,
            "action": "Confirmações",
            "detail": f"Confirmações faltantes: {mc}" if mc else "Todas as confirmações presentes"
        })
        
        # Step 6: Result
        steps.append({
            "step": 6,
            "action": "Resultado",
            "detail": f"Status: {op.get('status', 'N/A')} | Resultado: {op.get('result', 'N/A')}",
            "timestamp": op.get("closed_at", "N/A")
        })
        
        return steps


if __name__ == "__main__":
    run_server(ReplayMCPHandler, "leon-replay-mcp", "1.0.0")
