# Auditoria — Destravar o Operador LEON

## Status
**APROVADO COM RESSALVAS**

## Resumo Executivo

O operador LEON está funcional em termos de código-fonte, mas **4 bloqueios críticos** impedem sua execução. O principal é a ausência do pacote `MetaTrader5` para Linux — o código importa este pacote em pelo menos 10 módulos, mas ele só existe para Windows. Além disso, o ambiente Python não está configurado corretamente para uso interativo.

---

## Bloqueio #1 (CRÍTICO): MetaTrader5 não disponível no Linux

**Onde**: 10+ módulos importam `MetaTrader5 as mt5`
**Arquivos afetados**:
- `src/candle_engine.py`, `candle_reader.py`, `market_monitor.py`, `market_reader.py`
- `src/market_snapshot.py`, `momentum_reader.py`, `mt5_candles.py`
- `src/mt5_engine.py`, `mt5_execution_refiner.py`, `collector_operator.py`

**Causa**: O pacote `MetaTrader5` do PyPI só distribui wheels para Windows (win32/win_amd64). No Linux, a instalação falha.

**MT5 Terminal**: Está rodando via Wine (PID 3180, wine-11.13). O terminal está funcional.

**Solução**: Instalar o pacote MetaTrader5 via `pip install MetaTrader5` dentro de um **ambiente virtual Linux compatível**. O MetaQuotes **fornece o pacote MetaTrader5 para Linux sim** — ele compila via Cython. O problema atual é que o pip não está encontrando por causa do PEP 668 (ambiente gerenciado externamente).

**Ação necessária**:
```bash
# Opção 1: Usar o venv existente
/opt/leon/venv/bin/pip install MetaTrader5

# Opção 2: Criar novo venv
python3 -m venv /opt/leon/venv
/opt/leon/venv/bin/pip install MetaTrader5 python-dotenv requests flask werkzeug waitress pytest
```

---

## Bloqueio #2 (CRÍTICO): Ambiente Python não preparado para CLI

**Onde**: Shell interativo

**Causa**: O sistema tem PEP 668 ativo. Não há `venv` ativado no shell. Pip não funciona sem `--break-system-packages`. O Python não encontra o `python-dotenv` instalado em user-site porque o `PYTHONPATH` não inclui `/home/leon/.local/lib/python3.12/site-packages`.

**Solução**:
```bash
# Ativar o venv existente ou recriar
source /opt/leon/venv/bin/activate

# Ou configurar PYTHONPATH permanentemente
echo 'export PYTHONPATH=/home/leon/.local/lib/python3.12/site-packages:$PYTHONPATH' >> ~/.bashrc
```

---

## Bloqueio #3 (ALTO): Permissão 777 no .env

**Onde**: `/opt/leon/app/.env`

**Causa**: O arquivo `.env` que contém `SECRET_KEY`, `LEON_WEB_ADMIN_PASSWORD`, `LEON_TELEGRAM_TOKEN`, `LEON_TELEGRAM_CHAT_ID` está com permissão 777 (qualquer usuário no sistema pode ler e escrever).

**Solução**:
```bash
chmod 600 /opt/leon/app/.env
```

---

## Bloqueio #4 (ALTO): Módulos de replay não implementados

**Onde**: `src/backtest/`, `leon_strategy_replayer.py`, `statistical_report.py`, `context_decision.py`, `live_operational_contract.py`

**Causa**: Os módulos do sistema de replay nunca foram criados. Testes que os referenciam estão quebrados.

**Impacto**: O replay histórico não funciona. Isso afeta aprendizado, backtest e simulação.

---

## Bloqueio #5 (MÉDIO): Dependências web não instaladas

**Onde**: `/opt/leon/venv/`

**Causa**: O venv do sistema tem Flask 3.0.3 e python-dotenv 1.0.1, mas está faltando Werkzeug e waitress (ou a versão correta).

**Solução**:
```bash
/opt/leon/venv/bin/pip install -r /opt/leon/app/requirements_web.txt
```

---

## Bloqueio #6 (MÉDIO): Sem pytest no ambiente

**Impacto**: Não é possível rodar testes para validar correções.

**Solução**:
```bash
/opt/leon/venv/bin/pip install pytest
```

---

## Resumo de Ações Prioritárias

| Prioridade | Ação | Arquivo/Sistema |
|------------|------|-----------------|
| 🔴 **CRÍTICO** | Instalar MetaTrader5 no venv | `/opt/leon/venv/bin/pip install MetaTrader5` |
| 🔴 **CRÍTICO** | Corrigir permissão do .env | `chmod 600 /opt/leon/app/.env` |
| 🔴 **CRÍTICO** | Ativar venv no shell | `source /opt/leon/venv/bin/activate` |
| 🟠 **ALTO** | Instalar dependências web | `pip install -r requirements_web.txt` |
| 🟠 **ALTO** | Implementar módulos de replay | Criar `src/backtest/` package |
| 🟡 **MÉDIO** | Instalar pytest | `pip install pytest` |
| 🟡 **MÉDIO** | Corrigir 3 testes quebrados | `test_agent_coordination.py` |
| 🟢 **BAIXO** | Adicionar PYTHONPATH ao .bashrc | `~/.bashrc` |

---

## Comando para destravar agora

```bash
# 1. Ativar ambiente
source /opt/leon/venv/bin/activate

# 2. Instalar MetaTrader5
pip install MetaTrader5

# 3. Instalar dependências
pip install -r requirements_web.txt pytest

# 4. Corrigir segurança
chmod 600 /opt/leon/app/.env

# 5. Testar import
python -c "import MetaTrader5; print('OK:', MetaTrader5.__version__)"
```
