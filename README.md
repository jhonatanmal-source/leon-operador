# LEON Operador

Sistema local de analise, auditoria, aprendizado e operacao assistida para XAUUSD.

## Seguranca

- O repositorio remoto deve permanecer privado.
- Senhas, tokens, bancos, logs e dados de mercado nao pertencem ao Git.
- Use `.env.example` e `config.ini.example` como modelos locais.
- O backup integral permanece separado em `backups/`.

## Restauracao

1. Clone o repositorio.
2. Crie `.env` a partir de `.env.example`.
3. Crie `config.ini` a partir de `config.ini.example`.
4. Instale as dependencias indicadas nos arquivos `requirements`.
5. Restaure dados e banco somente a partir de um backup privado confiavel.

## Acesso ao painel

- Local: `http://127.0.0.1:5000/login`
- Remoto: Tailscale Funnel configurado no computador do operador.
