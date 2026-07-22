---
name: leon-security-review
description: Security review procedure — check credentials, permissions, SSH, firewall, dependencies, command injection, token exposure, .env protection.
---

## Objective
Identify and report security vulnerabilities.

## When to use
- Before any release
- Periodically for infrastructure
- When handling credentials or tokens

## Checklist
- [ ] No exposed credentials or tokens
- [ ] .env file properly protected
- [ ] SSH configured securely
- [ ] UFW firewall active
- [ ] No command injection vectors
- [ ] DEMO/REAL separation intact
- [ ] Real account blocked
- [ ] Dependencies checked for vulnerabilities

## Disclosure rule
If credentials are found exposed: record path only, do not display value, mark as risk, recommend fix.
