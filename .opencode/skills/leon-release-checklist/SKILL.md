---
name: leon-release-checklist
description: Release readiness checklist — verify tests, security, documentation, rollback plan, versioning, migrations, and configuration.
---

## Objective
Ensure releases are safe and complete.

## When to use
- Before any production release
- When the Release Manager is activated

## Checklist
- [ ] All tests pass
- [ ] Security review completed
- [ ] Documentation updated
- [ ] Rollback plan exists
- [ ] Version is updated
- [ ] Migrations are backward-compatible
- [ ] Configuration is validated
- [ ] Real account remains blocked
- [ ] No unauthorized changes

## Status
- APROVADO — all checks pass
- APROVADO COM RESSALVAS — minor issues documented
- REPROVADO — blocking issues found
- BLOQUEADO POR FALTA DE EVIDÊNCIA — insufficient verification
