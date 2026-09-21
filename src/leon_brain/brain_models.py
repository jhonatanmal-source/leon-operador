from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MemoryStatus(str, Enum):
    OBSERVATION = "OBSERVATION"
    HYPOTHESIS = "HYPOTHESIS"
    UNDER_VALIDATION = "UNDER_VALIDATION"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class BrainConclusion(str, Enum):
    FAVORABLE = "FAVORAVEL"
    UNFAVORABLE = "DESFAVORAVEL"
    INCONCLUSIVE = "INCONCLUSIVA"
    NO_EVIDENCE = "SEM_EVIDENCIA"


@dataclass
class BrainEvidence:
    evidence_id: str
    evidence_type: str
    source_mcp: str
    source_reference: str
    status: MemoryStatus
    relevance: float
    created_at: str
    summary: str


@dataclass
class OperationalBrainContext:
    timestamp: str
    symbol: str
    price: float
    macro_trend: str
    top_down_status: str
    session: str
    killzone: str
    direction: str
    smc_state: str
    elliott_state: str
    fibonacci_context: str
    liquidity_context: str
    zone_id: str
    zone_type: str
    zone_timeframe: str
    touch_status: str
    structural_confirmation: str
    missing_confirmations: list[str] = field(default_factory=list)
    current_blockers: list[str] = field(default_factory=list)
    strategy_version: str = ""
    operation_id: str = ""
    source_snapshot_id: str = ""


@dataclass
class MCPStatus:
    mcp_name: str
    available: bool
    error: Optional[str] = None
    response_time_ms: float = 0.0


@dataclass
class BrainResult:
    context: Optional[OperationalBrainContext] = None
    evidences: list[BrainEvidence] = field(default_factory=list)
    conclusion: BrainConclusion = BrainConclusion.NO_EVIDENCE
    summary: str = ""
    mcp_statuses: list[MCPStatus] = field(default_factory=list)
    total_time_ms: float = 0.0
    partial_result: bool = False
    shadow_mode: bool = True

    def can_execute(self) -> bool:
        return False

    def can_alter_order(self) -> bool:
        return False

    def can_alter_risk(self) -> bool:
        return False

    def can_alter_sl_tp(self) -> bool:
        return False
