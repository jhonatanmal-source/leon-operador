# Known Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| .env file permission 777 in /opt/leon/app/ | CRITICAL | chmod 600 |
| DEMO/REAL gate is single point of failure | HIGH | Add redundant check |
| Telegram logging broken on Linux | HIGH | Fix log paths |
| Replay modules not implemented | HIGH | Implement missing modules |
| Port 2090 exposed | HIGH | Investigate and secure |
