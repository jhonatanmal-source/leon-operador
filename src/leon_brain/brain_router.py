import json
import subprocess
import time
from pathlib import Path
from typing import Optional

from .brain_models import MCPStatus


ROOT_DIR = Path(__file__).resolve().parent.parent.parent


MCP_CONFIGS = {
    "leon-memory": {
        "command": ["python3", "src/mcp/leon_memory_mcp.py"],
        "timeout_ms": 500,
    },
    "leon-market": {
        "command": ["python3", "src/mcp/leon_market_mcp.py"],
        "timeout_ms": 500,
    },
    "leon-replay": {
        "command": ["python3", "src/mcp/leon_replay_mcp.py"],
        "timeout_ms": 500,
    },
    "leon-backtest": {
        "command": ["python3", "src/mcp/leon_backtest_mcp.py"],
        "timeout_ms": 500,
    },
}


class MCPRouter:

    def __init__(self, enabled_mcps: Optional[list[str]] = None):
        self.enabled_mcps = enabled_mcps or list(MCP_CONFIGS.keys())

    def _call_mcp(self, tool_name: str, arguments: dict, mcp_name: Optional[str] = None) -> dict:
        names = [mcp_name] if mcp_name else self.enabled_mcps
        results = {}

        for name in names:
            if name not in MCP_CONFIGS:
                results[name] = {"data": None, "time_ms": 0.0, "error": f"MCP {name} nao configurado"}
                continue

            cfg = MCP_CONFIGS[name]
            timeout_s = cfg["timeout_ms"] / 1000
            cmd = [str(ROOT_DIR / c) if c.startswith("src/") else c for c in cfg["command"]]

            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
                "id": 1,
            }

            start = time.time()
            try:
                proc = subprocess.run(
                    cmd,
                    input=json.dumps(request),
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                    cwd=str(ROOT_DIR),
                )
                elapsed = round((time.time() - start) * 1000, 2)

                if proc.returncode != 0:
                    results[name] = {"data": None, "time_ms": elapsed, "error": f"Codigo {proc.returncode}: {proc.stderr.strip()}"}
                    continue

                output = proc.stdout.strip()
                if not output:
                    results[name] = {"data": None, "time_ms": elapsed, "error": "Sem resposta do MCP"}
                    continue

                response = json.loads(output)
                if "error" in response:
                    results[name] = {"data": None, "time_ms": elapsed, "error": response["error"].get("message", "Erro desconhecido")}
                    continue

                content = response.get("result", {}).get("content", [])
                text = "\n".join(c.get("text", "") for c in content if c.get("type") == "text")
                parsed = None
                try:
                    parsed = json.loads(text) if text else None
                except json.JSONDecodeError:
                    parsed = {"raw": text}
                results[name] = {"data": parsed, "time_ms": elapsed, "error": None}

            except subprocess.TimeoutExpired:
                elapsed = round((time.time() - start) * 1000, 2)
                results[name] = {"data": None, "time_ms": elapsed, "error": f"Timeout apos {timeout_s}s"}
            except Exception as e:
                elapsed = round((time.time() - start) * 1000, 2)
                results[name] = {"data": None, "time_ms": elapsed, "error": str(e)}

        return results

    def consultar_todos(self, tool_name: str, arguments: dict) -> tuple[dict, list[MCPStatus]]:
        raw = self._call_mcp(tool_name, arguments)
        statuses = []
        data = {}

        for name, info in raw.items():
            statuses.append(MCPStatus(
                mcp_name=name,
                available=info["error"] is None,
                error=info["error"],
                response_time_ms=info["time_ms"],
            ))
            if info["data"] is not None:
                data[name] = info["data"]

        return data, statuses

    def consultar_mercado(self, contexto: Optional[dict] = None) -> tuple[Optional[dict], MCPStatus]:
        results, statuses = self.consultar_todos("get_market_context", contexto or {})
        for s in statuses:
            if s.mcp_name == "leon-market":
                return results.get("leon-market"), s
        return None, MCPStatus(mcp_name="leon-market", available=False, error="Nao encontrado")

    def consultar_memorias(self, contexto: dict) -> tuple[list, MCPStatus]:
        results, statuses = self.consultar_todos("search_memories", {"context": contexto})
        for s in statuses:
            if s.mcp_name == "leon-memory":
                memories = results.get("leon-memory", {})
                if isinstance(memories, dict):
                    return memories.get("memories", []), s
                return [], s
        return [], MCPStatus(mcp_name="leon-memory", available=False, error="Nao encontrado")

    def consultar_replay(self, contexto: dict) -> tuple[list, MCPStatus]:
        results, statuses = self.consultar_todos("search_replays", {"context": contexto})
        for s in statuses:
            if s.mcp_name == "leon-replay":
                replays = results.get("leon-replay", {})
                if isinstance(replays, dict):
                    return replays.get("replays", []), s
                return [], s
        return [], MCPStatus(mcp_name="leon-replay", available=False, error="Nao encontrado")

    def consultar_backtest(self, contexto: dict) -> tuple[list, MCPStatus]:
        results, statuses = self.consultar_todos("search_backtests", {"context": contexto})
        for s in statuses:
            if s.mcp_name == "leon-backtest":
                backtests = results.get("leon-backtest", {})
                if isinstance(backtests, dict):
                    return backtests.get("backtests", []), s
                return [], s
        return [], MCPStatus(mcp_name="leon-backtest", available=False, error="Nao encontrado")

    def registrar_observacao(self, observacao: dict) -> Optional[str]:
        results, statuses = self.consultar_todos("register_observation", observacao)
        for s in statuses:
            if s.mcp_name == "leon-memory":
                return None if s.available else s.error
        return "MCP leon-memory nao disponivel"

    def get_status(self) -> list[MCPStatus]:
        _, statuses = self.consultar_todos("list_tools", {})
        return statuses
