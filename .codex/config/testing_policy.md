# Testing Policy

## Required Tests
- Unit tests for all new code
- Integration tests for module boundaries
- Regression tests for bug fixes
- Edge case and negative tests for critical areas

## Critical Areas
- DEMO vs REAL classification
- MT5 connection and execution
- Risk limits (max 3 trades, daily loss)
- News shield blocking
- Zone and confirmation logic
- Telegram alerts
- Replay system
- Data persistence

## Prohibited
- Do not modify code to make tests pass
- Do not skip tests without documented reason
- Do not invent test results
