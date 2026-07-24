# Relat??rio de Corre????o ??? MT5 OFF na VPS

## Data
2026-07-23

## Status
**CORRIGIDO**

## Ambiente da VPS

| Item | Valor |
|------|-------|
| HOSTNAME | vps10098.panel.icontainer.net |
| SISTEMA | Linux 6.8.0-136-generic, Ubuntu 24.04 LTS |
| USU??RIO | leon (uid=1001) |
| SESSAO | headless (Xvfb :99 via xvfb-run) |
| PASTA DO PROJETO | /opt/leon/app |
| PYTHON | /opt/leon/venv/bin/python3 3.12.3 (64-bit) |
| PACOTES | mt5linux 1.0.3, rpyc 6.0.2 |
| MT5 | MetaTrader 5 build 500.6034 (18 Jul 2026) |
| MT5 PATH | /home/leon/.mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe |
| TERMINAL64 | ATIVO ??? 2 processos (PIDs 23372 desde Jul20, 127717 desde Jul22) |
| WINE | 11.13 (Staging) |
| RPYC BRIDGE | ATIVO ??? 127.0.0.1:18812 |
| DISPLAY | :99 (Xvfb) |
| CONTA | 207815 ?? FXGlobeInternational-Real ?? $10,000 USD |
| S??MBOLO XAU | Gold_Spot (select=True, spread=36) |
| XAUUSD | **N??O EXISTE** nesta corretora |
| INITIALIZE | True |
| LAST_ERROR | (1, 'Success') |
| TERMINAL CONNECTED | True |
| TRADE ALLOWED | True |

## Causa Raiz

Tr??s problemas independentes que juntos causavam o falso "MT5 OFF":

### 1. asset_detector.py ??? fallback incorreto

O s??mbolo `XAUUSD` **n??o existe** no servidor FXGlobeInternational-Real. O s??mbolo correto ?? `Gold_Spot`. O arquivo `CANDIDATOS = ["Gold_Spot", "XAUUSD", ...]` j?? listava `Gold_Spot` primeiro, mas a fun????o `detectar_ativo()` sempre retornava `"XAUUSD"` como fallback nas linhas 16-17, 20-21, e 42-43, ignorando que `Gold_Spot` existe.

Al??m disso, a verifica????o `if info and info.bid and info.bid > 0` impedia a detec????o correta em momentos de mercado fechado (bid=0 ou None), fazendo o c??digo cair no fallback incorreto.

### 2. mt5linux_compat.py ??? sem reconex??o ap??s shutdown

O wrapper singleton `_get_client()` criava o cliente RPyC uma ??nica vez. Quando qualquer m??dulo chamava `shutdown()`, a conex??o RPyC era fechada (`__conn.close()`), mas `_CLIENT` continuava apontando para o objeto com conex??o morta. Chamadas subsequentes de `initialize()` falhavam silenciosamente.

### 3. mt5_engine.py ??? obter_tick hardcoded

`obter_tick(simbolo="XAUUSD")` usava `"XAUUSD"` como padr??o. Como o s??mbolo n??o existe, `symbol_info_tick()` retornava None, e o c??digo interpretava isso como MT5 offline.

## Corre????es Aplicadas

### 1. `/opt/leon/app/src/asset_detector.py`
- Fallback alterado de `"XAUUSD"` para `CANDIDATOS[0]` (`"Gold_Spot"`)
- Removida verifica????o `info.bid and info.bid > 0` ??? se o s??mbolo existe e select funciona, ?? suficiente
- Fallback nos `except ImportError` e `if not mt5.initialize()` tamb??m corrigidos

### 2. `/opt/leon/app/mt5linux_compat.py`
- Adicionada fun????o `_reset_client()` que define `_CLIENT = None`
- `shutdown()` agora chama `_reset_client()` no `finally`
- `initialize()` chama `_reset_client()` em caso de exce????o, permitindo nova tentativa

### 3. `/opt/leon/app/src/mt5_engine.py`
- `obter_tick(simbolo=None)` ??? quando `None`, usa `detectar_ativo()` para obter o s??mbolo correto
- Import adicionado: `from asset_detector import detectar_ativo`

### 4. `/opt/leon/app/tarefas/diagnostico_mt5_vps.py` (novo)
- Script oficial de health check com estados distintos:
  - `MT5_OK`
  - `MT5_PROCESSO_NAO_EXECUTANDO`
  - `MT5_INITIALIZE_FALHOU`
  - `MT5_SEM_CONEXAO`
  - `MT5_SEM_CONTA`
  - `MT5_SIMBOLO_INDISPONIVEL`
  - `MT5_SEM_TICK`

## Config

O arquivo de configura????o `*.ini` j?? estava correto com `market_symbol = Gold_Spot` na se????o `[OPERATOR]`. Nenhuma altera????o necess??ria.

## Resultado dos Testes

### Teste 1 ??? MT5 conectado e operacional
```
initialize:     True
term_connected: True
acc_login:      207815
acc_balance:    10000.0
STATUS:         MT5_OK
```

### Teste 2 ??? Detec????o de ativo
```
Ativo detectado: Gold_Spot
```

### Teste 3 ??? obter_tick sem argumento
```
conectar: True
tick bid=4049.58 ask=4049.93
```

### Teste 4 ??? obter_tick com Gold_Spot expl??cito
```
conectar: True
Gold_Spot tick bid=4049.58 ask=4049.93
```

### Teste 5 ??? Reconex??o ap??s shutdown
```
conectar: True (ap??s shutdown anterior)
```

## Arquivos Modificados

| Arquivo | Backup |
|---------|--------|
| /opt/leon/app/src/asset_detector.py | asset_detector.py.bak |
| /opt/leon/app/mt5linux_compat.py | mt5linux_compat.py.bak |
| /opt/leon/app/src/mt5_engine.py | mt5_engine.py.bak |

## Arquivos Criados

| Arquivo | Descri????o |
|---------|-----------|
| /opt/leon/app/tarefas/diagnostico_mt5_vps.py | Health check oficial com estados |
| /opt/leon/app/tarefas/evidencias_mt5_vps/diagnostico_inicial.txt | Log do diagn??stico |

## Comando Que Apresentava MT5 OFF

Qualquer comando que chamasse `obter_tick()` sem s??mbolo expl??cito, ou que dependesse de `detectar_ativo()` para determinar o s??mbolo.

- **Antes**: retornava tick=None (XAUUSD inexistente) ??? c??digo interpretava como MT5 OFF
- **Depois**: retorna tick v??lido de Gold_Spot (bid=4049.22, ask=4049.54)

## Riscos Restantes

1. Se a VPS reiniciar, o MT5 e o RPyC bridge precisam ser reiniciados manualmente (n??o h?? systemd/service configurado)
2. Se o Wine corromper o prefixo `.mt5`, a inicializa????o pode falhar
3. O Xvfb run pode falhar se o display :99 estiver ocupado (usar `--auto-servernum`)

## Ordens Enviadas

**0** (zero) ??? nenhuma ordem real ou demo foi enviada durante o diagn??stico ou corre????o.

## Execu????o Real

**BLOQUEADA** ??? todas as verifica????es mantidas, `demo_only = true`, nenhuma regra de risco alterada.

## Prints

Os prints est??o dispon??veis em: `/opt/leon/app/tarefas/evidencias_mt5_vps/diagnostico_inicial.txt`

## Pr??xima A????o Recomendada

1. Configurar systemd para rein??cio autom??tico do MT5 + RPyC bridge em caso de reboot da VPS
2. Testar fluxo completo `leon_operator` com as corre????es aplicadas
3. Se desejar, remover o segundo terminal64.exe em excesso (PID 127717)
