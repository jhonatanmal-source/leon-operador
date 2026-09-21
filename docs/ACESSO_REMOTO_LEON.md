# ACESSO REMOTO LEON WEB COLLAB

Este modo não usa MikroTik.

Não precisa abrir portas.

Não precisa VPS.

Não precisa domínio.

O PC do LEON precisa ficar ligado.

O painel web unificado roda localmente em:

`http://127.0.0.1:5000`

O Cloudflare Tunnel gera um link temporário semelhante a:

`https://algum-nome.trycloudflare.com`

O link muda quando o túnel é fechado e aberto novamente.

## Como iniciar

1. Rodar `python setup_web_collab.py`.
2. Rodar `python setup_remote_access.py`.
3. Rodar `ATALHOS_LEON\ACESSO_REMOTO\02_INICIAR_WEB_E_TUNEL.bat`.
4. Copiar o link `trycloudflare.com` exibido na janela do Cloudflare.
5. Entrar com o usuário administrador criado no setup.
6. Acessar o menu `Painel Leon` dentro do painel web.
7. Enviar o link somente para operadores autorizados.

## Regras de segurança

- Nunca compartilhar o link publicamente.
- Trocar a senha inicial do administrador logo no primeiro acesso.
- Não colocar execução de ordem no painel.
- Não expor o MT5.
- Não expor token do Telegram.
- Não expor o arquivo `.env`.
- Usar senha forte e exclusiva.
- Cada operador deve ter usuário próprio.
- O painel serve para supervisão, estudo humano e visualização remota.
