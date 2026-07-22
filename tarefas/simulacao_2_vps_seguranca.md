# Simulação 2 — VPS Ubuntu 24.04

## Missão
Analise a VPS Ubuntu 24.04 e indique riscos de segurança.

## Classificação
SEGURANÇA / INFRAESTRUTURA

## Agentes escolhidos
- Engineering Director (coordenação)
- DevOps Engineer (infraestrutura)
- Security Engineer (segurança)

## Risco crítico
1. **`/opt/leon/app/.env` com permissão 777 (world-readable)** — Contém SECRET_KEY, LEON_WEB_ADMIN_PASSWORD, LEON_TELEGRAM_TOKEN, LEON_TELEGRAM_CHAT_ID. Qualquer usuário no sistema pode ler.
2. **Duplicata do .env** — Arquivo em `/opt/leon/app/.env` é cópia de `/opt/leon/config/.env` mas com permissões inseguras.

## Riscos altos
3. **Banco de dados world-readable** — `/opt/leon/data/leon_web.db` em 644.
4. **Porta 2090 exposta** — Serviço não identificado em todas as interfaces.

## Riscos médios
5. **Logs world-readable** — Propriedade root com 644.
6. **Diretório .git em 775** — Permissão muito permissiva.

## Pontos positivos
- Config files em 600
- SSH configurado corretamente (700/600)
- Service hardening (NoNewPrivileges, PrivateTmp, ProtectSystem)
- Git hygiene (.env ignorado, sem segredos no histórico)
- Sem credenciais hardcoded no código fonte

## Conclusão
Sistema com boa base de segurança, mas com falha crítica de permissão no `.env` que expõe todas as credenciais.

## Nenhuma alteração funcional realizada
Modo somente leitura respeitado.
