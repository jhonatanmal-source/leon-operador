---
name: leon-change-impact-analysis
description: Impact analysis for proposed changes — identify affected modules, risk of regression, test coverage needed, and rollback complexity.
---

## Objective
Assess the impact of changes before implementation.

## When to use
- Before starting implementation
- When evaluating a proposed change

## Procedure
1. Identify all modules that will be affected
2. Assess regression risk (low/medium/high)
3. Check existing test coverage
4. Determine if rollback is possible
5. Identify dependencies that may break
6. Estimate implementation effort

## Output
- List of affected modules
- Risk assessment
- Test coverage gaps
- Rollback strategy
- Recommendation (proceed/caution/block)
