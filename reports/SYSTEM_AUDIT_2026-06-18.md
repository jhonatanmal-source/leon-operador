# AUDITORIA GERAL — LEON XAU ELITE AI

Data: 18 de junho de 2026

Escopo:

- Operador 24h
- Fluxo de análise
- Executor MT5 demo
- Risco e autonomia
- Memórias e operações-sombra
- Telegram
- Painel legado
- LEON WEB COLLAB
- Cloudflare Tunnel

## Resumo executivo

O sistema principal está online, compilando e coletando dados. O MT5 está conectado
em conta demo, com negociação e API permitidas. O watchdog não detectou erros
críticos recentes.

O LEON não envia ordens atualmente porque não há pré-operação aberta. O bloqueio
é causado pelo setup não confirmar Fibonacci e captura de liquidez ao mesmo tempo.

Foram compilados com sucesso 192 arquivos Python.

## Estado atual

- Operador 24h: ONLINE
- Painel legado: ONLINE
- WEB COLLAB: ONLINE
- Cloudflare Tunnel: ONLINE
- MT5: ONLINE / DEMO
- Coletor: OK
- Watchdog: OK
- Prontidão para operação real: OBSERVAÇÃO
- Pré-operações totais: 177
- Pré-operações fechadas: 55
- Wins registrados: 25
- Losses registrados: 13
- Taxa calculada atual: 45,45%
- Operações-sombra: 2 abertas

## Pontos positivos

1. O executor está limitado a conta demo.
2. O MT5 está conectado e permite negociação automatizada.
3. O operador, coletor e análises automáticas estão ativos.
4. O painel web não contém rotas para enviar ordens.
5. O painel web não expõe token Telegram ou login da corretora.
6. Uploads aceitam somente JPG, JPEG e PNG e validam assinatura básica.
7. Senhas web são armazenadas com hash.
8. O administrador já trocou a senha inicial.
9. A chave de sessão padrão foi substituída por chave aleatória durante a auditoria.
10. O painel de saúde é somente leitura.

## Achados críticos e altos

### [ALTO] Token Telegram armazenado em texto puro

O token e o chat ID estão presentes diretamente no `config.ini`.

Risco:

- Cópias, backups, compartilhamento de tela ou leitura indevida do arquivo podem
  comprometer o bot.

Recomendação:

- Revogar e gerar novo token no BotFather.
- Armazenar token e chat ID somente no `.env`.
- Remover os valores sensíveis do `config.ini`.

### [ALTO] Escopo de autonomia não é aplicado pelo executor

O `config.ini` declara `scope=learning_only`, mas o executor MT5 não consulta o
escopo da autonomia antes de enviar uma ordem demo.

Risco:

- O texto do escopo transmite uma proteção que não é tecnicamente aplicada.

Recomendação:

- Criar política explícita de escopos.
- Exigir um escopo como `demo_execution` antes do executor.
- Manter conta real bloqueada independentemente do escopo.

### [ALTO] Quick Tunnel público sem Cloudflare Access

O link `trycloudflare.com` é público para quem o conhecer. O login do painel ainda
protege o conteúdo, mas não há uma camada externa de identidade Cloudflare.

Recomendação:

- Para uso contínuo, trocar Quick Tunnel por Named Tunnel.
- Configurar Cloudflare Access com e-mail autorizado ou OTP.
- Não publicar o link em grupos abertos.

### [ALTO] Proteções web incompletas contra ataques automatizados

O painel possui autenticação e roles, mas ainda não possui:

- CSRF token nos formulários POST.
- Limite de tentativas de login.
- Bloqueio temporário por IP/usuário.

Recomendação:

- Adicionar proteção CSRF.
- Adicionar rate limiting no login.
- Registrar e alertar tentativas repetidas.

### [ALTO] Servidor Flask de desenvolvimento exposto pelo túnel

O painel usa o servidor embutido do Flask. Ele funciona, porém não é recomendado
para exposição contínua.

Recomendação:

- Usar Waitress no Windows.
- Manter o Flask ligado somente em `127.0.0.1`.
- Deixar o Cloudflare Tunnel como única entrada externa.

## Achados médios

### [MÉDIO] Elliott pode exibir ONDA 3 sem Fibonacci válido

O contexto Elliott pode receber o rótulo `ONDA 3` pela estrutura parcial mesmo
quando `fibonacci_setup.valid` é falso.

Impacto:

- A ordem continua bloqueada corretamente.
- O painel e os relatórios podem confundir “contexto provável” com “setup válido”.

Recomendação:

- Exibir `POSSÍVEL ONDA 3` quando Fibonacci não estiver confirmado.
- Reservar `ONDA 3 CONFIRMADA` para Fibonacci + SMC completos.

### [MÉDIO] Operações-sombra duplicadas por mudança de bloqueio

A assinatura inclui a lista de confirmações faltantes. O mesmo BOS/CHOCH pode gerar
mais de uma sombra quando o top-down muda.

Recomendação:

- Deduplicar por evento estrutural principal.
- Registrar mudanças de confirmação como histórico da mesma sombra.

### [MÉDIO] Taxa simulada mistura resultados diferentes

Existem 55 operações fechadas, mas apenas 25 wins e 13 losses. Outros estados
fechados entram no denominador da taxa.

Impacto:

- A taxa de 45,45% é conservadora, mas não representa apenas win/loss.

Recomendação:

- Exibir duas métricas:
  - Win rate decidido: wins / (wins + losses).
  - Taxa global: wins / todos os fechamentos.

### [MÉDIO] Caminhos absolutos espalhados pelo projeto

Diversos módulos usam `C:/XAU_ELITE_AI` diretamente.

Impacto:

- Dificulta mover o projeto, testar em outra pasta ou restaurar em outra máquina.

Recomendação:

- Centralizar `BASE_DIR`.
- Migrar gradualmente para `pathlib.Path`.

## Achados baixos e dívida técnica

1. Existem módulos antigos e placeholders que não participam do fluxo atual.
2. `health_check.py` apenas imprime mensagens e não valida componentes.
3. `analysis/setup_score.py` usa score fixo.
4. `session_engine.py` possui sessão fixa.
5. `execution_guard.py` é um stub permanentemente falso.
6. Há código duplicado entre `choch_engine.py` e `teste_choch.py`.
7. Existem vários motores antigos de momentum, entrada e SMC ainda no repositório.
8. Testes são scripts avulsos; alguns podem enviar Telegram ou acessar MT5.

Recomendação:

- Separar claramente `core_atual`, `legacy` e `tests`.
- Criar suíte de testes que nunca envie mensagens ou ordens.
- Arquivar módulos não utilizados após confirmar dependências.

## Prioridade recomendada

1. Rotacionar o token Telegram e migrá-lo para `.env`.
2. Aplicar escopo real de autonomia ao executor.
3. Adicionar CSRF e limite de login ao WEB COLLAB.
4. Trocar Flask dev server por Waitress.
5. Criar Named Tunnel com Cloudflare Access.
6. Corrigir nomenclatura Elliott/Fibonacci.
7. Corrigir deduplicação das operações-sombra.
8. Separar win rate decidido da taxa global.
9. Reduzir caminhos absolutos e módulos legados.

## Conclusão

O sistema está operacional e saudável, mas ainda possui riscos de segurança e
consistência que devem ser tratados antes de qualquer consideração de conta real.
O modo demo deve permanecer obrigatório.
