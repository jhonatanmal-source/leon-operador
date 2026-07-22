---
name: leon-observability-standard
description: Observability standards for logs, metrics, health checks, error messages, tracing, and monitoring across the LEON system.
---

## Objective
Establish consistent observability practices.

## When to use
- When creating or reviewing logging
- When setting up monitoring
- When debugging production issues

## Standards
- All logs include timestamp and severity level
- Error messages include context and correlation ID
- Health checks exist for critical services
- Metrics for CPU, memory, and latency
- Log rotation is configured
- No sensitive data in logs

## Checklist
- [ ] Structured logging format
- [ ] Correlation IDs in async operations
- [ ] Health check endpoints
- [ ] Error alerting configured
- [ ] Log growth monitored
