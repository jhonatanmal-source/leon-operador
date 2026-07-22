---
name: leon-mt5-safety
description: MT5 safety rules — never send orders, never release real account, never modify execution logic, always verify DEMO/REAL classification.
---

## Objective
Prevent any unsafe MT5 operation during development and testing.

## When to use
- Any task involving MT5 modules
- When reviewing MT5-related code

## Absolute prohibitions
- Sending MT5 orders is FORBIDDEN
- Real account release is FORBIDDEN
- Modifying execution logic is FORBIDDEN
- Removing safety guards is FORBIDDEN

## Verification
- Always check DEMO/REAL classification
- Verify risk limits are intact
- Confirm news shield is operational
- Confirm max 3 trades per day limit
