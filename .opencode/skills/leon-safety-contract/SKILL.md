---
name: leon-safety-contract
description: Safety rules that all agents must follow — never alter strategy, risk, TP/SL, MT5 execution, real account, or expose secrets.
---

## Objective
Ensure all agents operate within safety boundaries.

## When to use
- Before any code modification
- When reviewing changes for safety compliance

## When not to use
- During read-only analysis

## Safety contract
- No MT5 order sending
- No automatic operation start
- No real account release
- No guard removal
- No strategy, risk, TP/SL changes
- No credential exposure
- No commit/push without authorization
- No destructive commands

## Violation procedure
1. Stop immediately
2. Record the violation in checkpoint
3. Inform the Engineering Director
