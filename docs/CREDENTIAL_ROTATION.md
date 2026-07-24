# Rotacao de Credenciais - 2026-07-24

## Motivo

As credenciais do projeto estavam expostas em texto plano no arquivo `.env`. Isso representa um risco de seguranca, pois qualquer pessoa com acesso ao codigo fonte ou ao historico do repositorio poderia utilizar os tokens e senhas para acessar sistemas externos (Telegram, admin panel, etc.).

Para eliminar esse risco, todas as credenciais foram rotacionadas nesta data.

## O que foi alterado

| Credencial | Acao |
|---|---|
| `SECRET_KEY` | Novo token gerado. Substituir o valor antigo pelo novo no `.env`. |
| `LEON_WEB_ADMIN_PASSWORD` | Nova senha definida (substituir no `.env` se necessario) |
| `LEON_TELEGRAM_TOKEN` | Marcado como `COLAR_NOVO_TOKEN_AQUI_APOS_ROTACIONAR_NO_BOTFATHER` |
| `LEON_TELEGRAM_CHAT_ID` | Marcado como `ATUALIZAR_CHAT_ID` |
| `LEON_TELEGRAM_ENABLED` | Desabilitado (`false`) ate que o novo token do Telegram seja configurado |

## Instrucoes para rotacionar o token Telegram

O token do Telegram precisa ser revogado e recriado diretamente pelo BotFather. Siga os passos abaixo:

1. Abra o Telegram e inicie uma conversa com [@BotFather](https://t.me/BotFather).
2. Envie o comando `/mybots`.
3. Selecione o bot **LEON XAU ELITE AI** na lista.
4. No menu do bot, clique em **API Token**.
5. Clique em **Revoke current token** para revogar o token antigo.
6. Copie o novo token gerado pelo BotFather.
7. Abra o arquivo `.env` e substitua o valor de `LEON_TELEGRAM_TOKEN` pelo novo token.
8. Altere `LEON_TELEGRAM_ENABLED` para `true`.
9. Salve o arquivo e reinicie o servico do LEON.

```bash
# Apos configurar o novo token, reiniciar o servico:
sudo systemctl restart leon
```

## Seguranca

- O arquivo `.env` ja esta incluido no `.gitignore` e **nunca deve ser commitado** no repositorio.
- Nenhuma credencial ativa deve estar presente em arquivos de documentacao, codigo fonte ou logs.
- Em caso de duvida sobre exposicao de credenciais, repita o processo de rotacao imediatamente.

## Recomendacao

Para versoes futuras, recomenda-se a adocao de um vault criptografado (ex.: HashiCorp Vault, Ansible Vault ou `python-dotenv` com arquivo cifrado) para gerenciar credenciais em ambiente de producao, eliminando a dependencia de texto plano.
