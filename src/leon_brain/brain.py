import os
import time
from typing import Optional

from .brain_models import (
    BrainConclusion,
    BrainEvidence,
    BrainResult,
    MCPStatus,
    MemoryStatus,
    OperationalBrainContext,
)
from .brain_context import build_context, context_to_dict
from .brain_explainer import generate_short_summary, generate_panel_block
from .brain_memory import BrainMemory
from .brain_patterns import find_patterns
from .brain_professor import BrainProfessor
from .brain_router import MCPRouter
from .brain_validator import BrainValidator


FLAGS = {
    "LEON_BRAIN_ENABLED": os.environ.get("LEON_BRAIN_ENABLED", "false").lower() == "true",
    "LEON_BRAIN_SHADOW_MODE": os.environ.get("LEON_BRAIN_SHADOW_MODE", "true").lower() == "true",
    "LEON_BRAIN_MARKET_ENABLED": os.environ.get("LEON_BRAIN_MARKET_ENABLED", "true").lower() == "true",
    "LEON_BRAIN_MEMORY_ENABLED": os.environ.get("LEON_BRAIN_MEMORY_ENABLED", "true").lower() == "true",
    "LEON_BRAIN_REPLAY_ENABLED": os.environ.get("LEON_BRAIN_REPLAY_ENABLED", "true").lower() == "true",
    "LEON_BRAIN_BACKTEST_ENABLED": os.environ.get("LEON_BRAIN_BACKTEST_ENABLED", "true").lower() == "true",
    "LEON_BRAIN_TIMEOUT_MS": int(os.environ.get("LEON_BRAIN_TIMEOUT_MS", "500")),
    "LEON_BRAIN_MAX_MEMORY_RESULTS": int(os.environ.get("LEON_BRAIN_MAX_MEMORY_RESULTS", "10")),
    "LEON_BRAIN_MAX_REPLAY_RESULTS": int(os.environ.get("LEON_BRAIN_MAX_REPLAY_RESULTS", "5")),
    "LEON_BRAIN_MAX_BACKTEST_RESULTS": int(os.environ.get("LEON_BRAIN_MAX_BACKTEST_RESULTS", "5")),
    "LEON_BRAIN_REGISTER_OBSERVATIONS": os.environ.get("LEON_BRAIN_REGISTER_OBSERVATIONS", "false").lower() == "true",
    "LEON_BRAIN_PANEL_ENABLED": os.environ.get("LEON_BRAIN_PANEL_ENABLED", "true").lower() == "true",
    "LEON_BRAIN_TELEGRAM_ENABLED": os.environ.get("LEON_BRAIN_TELEGRAM_ENABLED", "false").lower() == "true",
}


class LeonBrain:

    def __init__(self):
        enabled_mcps = []
        if FLAGS["LEON_BRAIN_MARKET_ENABLED"]:
            enabled_mcps.append("leon-market")
        if FLAGS["LEON_BRAIN_MEMORY_ENABLED"]:
            enabled_mcps.append("leon-memory")
        if FLAGS["LEON_BRAIN_REPLAY_ENABLED"]:
            enabled_mcps.append("leon-replay")
        if FLAGS["LEON_BRAIN_BACKTEST_ENABLED"]:
            enabled_mcps.append("leon-backtest")

        self._router = MCPRouter(enabled_mcps=enabled_mcps)
        self._memory = BrainMemory(self._router)
        self._professor = BrainProfessor()
        self._validator = BrainValidator()
        self._shadow_mode = FLAGS["LEON_BRAIN_SHADOW_MODE"]

    @property
    def is_enabled(self) -> bool:
        return FLAGS["LEON_BRAIN_ENABLED"]

    @property
    def is_shadow_mode(self) -> bool:
        return self._shadow_mode

    def process_context(self, context: OperationalBrainContext) -> BrainResult:
        start = time.time()
        result = BrainResult(shadow_mode=self._shadow_mode)

        if not self.is_enabled:
            result.summary = "LEON BRAIN desligado. Comportamento identico ao atual."
            result.total_time_ms = round((time.time() - start) * 1000, 2)
            return result

        result.context = context
        ctx_dict = context_to_dict(context)

        context_summary = f"{context.symbol} | {context.direction} | {context.smc_state} | {context.session}"

        market_data, mcp_status = self._router.consultar_mercado(ctx_dict)
        result.mcp_statuses.append(mcp_status)

        memories = self._memory.consultar(ctx_dict, max_results=FLAGS["LEON_BRAIN_MAX_MEMORY_RESULTS"])
        result.evidences.extend(memories)

        replay_data = []
        if FLAGS["LEON_BRAIN_REPLAY_ENABLED"]:
            replay_data, _ = self._router.consultar_replay(ctx_dict)

        backtest_data = []
        if FLAGS["LEON_BRAIN_BACKTEST_ENABLED"]:
            backtest_data, _ = self._router.consultar_backtest(ctx_dict)

        patterns = find_patterns(context, result.evidences, [m.__dict__ for m in memories])

        result.conclusion = self._professor.gerar_conclusao(result.evidences, patterns)
        result.summary = self._professor.gerar_explicacao(context_summary, result.evidences, patterns)

        validated = self._memory.filtrar_validados(result.evidences)
        if not validated:
            result.partial_result = True

        violations = self._validator.validate_result(result)
        if violations:
            result.summary += "\n\nVIOLACAO DE SEGURANCA DETECTADA:\n" + "\n".join(violations)

        if market_data and FLAGS["LEON_BRAIN_REGISTER_OBSERVATIONS"]:
            self._memory.registrar({
                "type": "OBSERVATION",
                "context": ctx_dict,
                "conclusion": result.conclusion.value,
            })

        result.total_time_ms = round((time.time() - start) * 1000, 2)
        return result

    def generate_summary(self, result: BrainResult) -> str:
        return generate_short_summary(result)

    def generate_panel_block(self, result: BrainResult) -> str:
        return generate_panel_block(result)
