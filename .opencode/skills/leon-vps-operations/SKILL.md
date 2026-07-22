---
name: leon-vps-operations
description: VPS operations guide for Ubuntu 24.04 — SSH, UFW, systemd, Docker, logs, backups, health checks, watchdog, monitoring, deploy, rollback.
---

## Objective
Standardize VPS operational procedures.

## When to use
- When performing infrastructure tasks
- When diagnosing VPS issues

## Key areas
- SSH key-based auth only
- UFW with minimal open ports
- systemd service management
- Docker Compose for containerized services
- Log rotation configured
- Automated backups verified
- Health check endpoints operational
- Watchdog for critical services

## Safety
- Validate config before restarting services
- Never expose ports unnecessarily
- Never reveal connection secrets
