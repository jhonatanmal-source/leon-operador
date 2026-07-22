---
name: leon-testing-protocol
description: Standard testing protocol for LEON — unit tests, integration tests, regression tests, edge cases, negative tests, and validation of critical areas.
---

## Objective
Standardize testing procedures across the team.

## When to use
- Before releasing any change
- When QA validation is required

## Critical test areas
- DEMO vs REAL classification
- MT5 connection and execution
- Risk limits (max 3 trades, daily loss)
- PRE_OPERATION state
- Zones and confirmations
- News shield blocking
- Telegram alerts
- Replay system
- Persistence

## Procedure
1. Run focused tests for the changed module
2. Run regression suite
3. Verify no false positives
4. Document results with evidence

## Rejection criteria
- Tests fail without clear explanation
- Critical area untested
- Test results cannot be reproduced
