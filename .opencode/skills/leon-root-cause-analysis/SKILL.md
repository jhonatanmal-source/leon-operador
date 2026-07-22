---
name: leon-root-cause-analysis
description: Systematic root cause analysis procedure — reproduce the failure, gather evidence, identify cause, propose fix, create regression test.
---

## Objective
Conduct thorough root cause analysis with evidence.

## When to use
- When investigating bugs or failures
- Before implementing any fix

## When not to use
- For architectural analysis or feature development

## Procedure
1. Reproduce the failure
2. Gather evidence (logs, traces, error messages)
3. Identify root cause
4. Create a regression test
5. Propose minimal fix
6. Validate fix with tests

## Approval criteria
- Root cause is identified with evidence
- Regression test passes
- No side effects on other functionality
