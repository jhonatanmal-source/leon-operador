# Guia Rápido — Comandos LEON

## Comandos Disponíveis

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `/leon-missao` | Enviar missão ao Engineering Director | `/leon-missao Corrigir falha no Telegram sem alterar MT5` |
| `/leon-auditoria` | Auditoria somente leitura | `/leon-auditoria Segurança da VPS` |
| `/leon-corrigir` | Investigar e corrigir bug | `/leon-corrigir Erro ao persistir PRE_OPERATION` |
| `/leon-testar` | Executar testes | `/leon-testar Testes focados do módulo de zonas` |
| `/leon-revisar` | Revisar alterações | `/leon-revisar` |
| `/leon-status` | Verificar status da missão | `/leon-status` |
| `/leon-retomar` | Retomar missão interrompida | `/leon-retomar` |
| `/leon-relatorio` | Gerar relatório consolidado | `/leon-relatorio missão Telegram` |

## Fluxo Recomendado

1. **Iniciar missão**: `/leon-missao <descrição>`
2. **Acompanhar**: `/leon-status` (a qualquer momento)
3. **Revisar**: `/leon-revisar` (após implementação)
4. **Testar**: `/leon-testar` (antes do relatório)
5. **Relatar**: `/leon-relatorio <missão>`
6. **Retomar**: `/leon-retomar` (se interrompido)

## Segurança

- Nenhum comando envia ordens MT5
- Nenhum comando libera conta real
- Nenhum comando altera estratégia
- Nenhum comando faz commit/push
- Todos os comandos mantêm guards ativos
