---
name: 10-telegram
description: Messages, commands, alerts, context, readability, security, authentication, reports, token protection for Telegram integration.
---

# 10-telegram

## Identificador
`telegram-skill`

## Objetivo
Gerenciar mensagens, comandos, alertas e relatórios do Telegram com segurança.

## Quando acionar
- Configuração/ manutenção do módulo Telegram
- Criação de novos alertas

## Responsabilidades
- Mensagens e comandos
- Alertas e contexto
- Legibilidade e segurança
- Autenticação e relatórios
- Proteção de tokens

## Regras
- Nunca exibir token ou CHAT_ID
- Não enviar mensagens duplicadas em curto intervalo
- Validar entrada antes de enviar

## Arquivos protegidos
- Token e CHAT_ID (nunca exibir)
