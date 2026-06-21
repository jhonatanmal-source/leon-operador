LEON XAU AI - USO DIARIO

Abra esta pasta todos os dias e clique em:

01_ABRIR_LEON_TODO_DIA.bat

Esse botao faz quatro coisas:

1. Liga o painel local.
2. Liga o operador do LEON.
3. Concede autonomia por 8 horas.
4. Envia um checkpoint para o Telegram.

Painel:
http://127.0.0.1:8765/

Observacao importante:
Para o LEON aprender durante o dia, o computador precisa ficar ligado, com internet,
MetaTrader 5 disponivel e o operador rodando.

Se quiser apenas conferir:
- 02_ABRIR_SOMENTE_PAINEL.bat
- 05_ENVIAR_STATUS_TELEGRAM.bat

Se quiser renovar o tempo de autonomia:
- 04_DAR_AUTONOMIA_8H.bat

Se quiser que o LEON abra sozinho todo dia ao ligar o Windows:
- 06_COLOCAR_LEON_NA_INICIALIZACAO_WINDOWS.bat

Se quiser remover essa abertura automatica:
- 07_REMOVER_LEON_DA_INICIALIZACAO_WINDOWS.bat
ROTINA AUTOMATICA WINDOWS
=========================

08_INICIAR_LEON_E_CODEX.bat
- Abre painel do LEON.
- Abre operador 24h.
- Tenta abrir Codex automaticamente.

09_COLOCAR_LEON_E_CODEX_NA_INICIALIZACAO.bat
- Cria atalho na inicializacao do Windows.
- Depois do login, o LEON sobe sozinho.

10_REMOVER_LEON_E_CODEX_DA_INICIALIZACAO.bat
- Remove o atalho da inicializacao.

11_REINICIAR_WINDOWS_E_VOLTAR_COM_LEON.bat
- Reinicia o Windows com confirmacao.
- Use depois de executar o script 09.

Observacao:
- Se o Codex nao abrir automaticamente, abra manualmente uma vez e informe o caminho do atalho.
- O operador continua respeitando modo demo, risco, RR e protecoes.
