# LEON BRAIN V1 — Architecture Report

## Directory Structure
src/leon_brain/
    __init__.py
    brain.py
    brain_models.py
    brain_context.py
    brain_router.py
    brain_memory.py
    brain_patterns.py
    brain_professor.py
    brain_explainer.py
    brain_validator.py
    brain_checkpoint.py

## Modules

| Module | Responsibility |
|--------|---------------|
| brain.py | Orchestrator — processes context, coordinates MCPs, generates result |
| brain_models.py | Data classes: OperationalBrainContext, BrainEvidence, BrainResult, enums |
| brain_context.py | Builds normalized context from operator data |
| brain_router.py | Communicates with MCPs (market, memory, replay, backtest) via stdio JSON-RPC |
| brain_memory.py | Queries leon-memory, filters by status |
| brain_patterns.py | Context comparison, similarity scoring, pattern recognition |
| brain_professor.py | Evidence-based explanation generation |
| brain_explainer.py | Short summaries for panel and Telegram |
| brain_validator.py | Guards — ensures BrainResult can never execute, alter orders, risk, SL/TP |
| brain_checkpoint.py | Integrates LEON BRAIN block into checkpoint JSON |

## MCPs Integrated
- leon-market (market context)
- leon-memory (memory search + observation registration)
- leon-replay (historical replay search)
- leon-backtest (backtest result search)

## Key Design Decisions
1. Shadow mode by default — no operational impact until explicitly enabled
2. Feature flags via environment variables — LEON_BRAIN_ENABLED=false preserves existing behavior
3. MCP failures are non-blocking — partial results with degraded MCP set
4. BrainResult is immutable regarding execution — can_execute(), can_alter_order(), etc. always return False
5. Memory never confirms entry — purely contextual
