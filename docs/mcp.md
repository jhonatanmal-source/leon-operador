# LEON MCP Servers

## Visão Geral

O LEON possui 4 servidores MCP (Model Context Protocol) que expandem suas capacidades de memória, dados de mercado, backtesting e replay. Todos operam sobre JSON-RPC 2.0 via stdio e são gerenciados pelo OpenCode.

## Arquitetura

```
src/mcp/
├── mcp_protocol.py          # Base handler do protocolo MCP
├── _mt5_safe.py             # Wrapper read-only para MT5 (bloqueia ordens)
├── leon_memory_mcp.py       # Memory MCP - 6 tools
├── leon_market_mcp.py       # Market MCP - 7 tools
├── leon_backtest_mcp.py     # Backtest MCP - 4 tools
└── leon_replay_mcp.py       # Replay MCP - 5 tools
```

## Configuração

Os MCPs são registrados em `opencode.json`:

```json
{
  "mcpServers": {
    "leon-memory": {
      "type": "stdio",
      "command": "python3",
      "args": ["src/mcp/leon_memory_mcp.py"]
    },
    "leon-market": {
      "type": "stdio",
      "command": "python3",
      "args": ["src/mcp/leon_market_mcp.py"]
    },
    "leon-backtest": {
      "type": "stdio",
      "command": "python3",
      "args": ["src/mcp/leon_backtest_mcp.py"]
    },
    "leon-replay": {
      "type": "stdio",
      "command": "python3",
      "args": ["src/mcp/leon_replay_mcp.py"]
    }
  }
}
```

---

## 1. Memory MCP (`leon-memory-mcp`)

**Propósito**: Memória auxiliar, acesso ao vault Obsidian, busca de contexto e aprendizado diário.

### Tools

| Tool | Descrição | Parâmetros |
|------|-----------|------------|
| `get_daily_context` | Retorna CONTEXTO_EVOLUCAO.md para carregamento rápido | — |
| `search_knowledge_base` | Busca notas no vault Obsidian | `query` (req), `max_results` (10) |
| `store_note` | Cria nova nota no vault (sem sobrescrita) | `title` (req), `content` (req), `folder` |
| `register_learning` | Registra aprendizado no diário | `content` (req), `date`, `category` |
| `list_recent_learnings` | Lista aprendizados recentes | `days` (7) |
| `get_vault_structure` | Mostra estrutura do vault | — |

### Segurança
- Notas novas apenas (modo `x` ou append, nunca `w`)
- Sem deleção de arquivos
- Sincroniza com `tarefas/aprendizados_diarios/`

---

## 2. Market MCP (`leon-market-mcp`)

**Propósito**: Coleta de dados de mercado. **APENAS LEITURA**.

### Tools

| Tool | Descrição | Parâmetros |
|------|-----------|------------|
| `check_mt5_status` | Verifica disponibilidade do MT5 | — |
| `get_current_price` | Preço atual (bid/ask) | `symbol` (req) |
| `get_symbol_info` | Informações do símbolo | `symbol` (req) |
| `get_ohlc` | Dados OHLC históricos | `symbol` (req), `timeframe` (15), `count` (20) |
| `list_symbols` | Lista símbolos disponíveis | `filter` |
| `get_account_info` | Info da conta (read-only) | — |
| `get_market_snapshot` | Snapshot completo de múltiplos símbolos | `symbols` (["XAUUSD"]) |

### Segurança
- Usa `_mt5_safe.py` que **BLOQUEIA**: `order_send`, `order_check`, `login`, `initialize`, `shutdown`, `eval`, `execute`
- Apenas 5 funções read-only expostas
- Nenhuma chamada a funções de escrita é possível

---

## 3. Backtest MCP (`leon-backtest-mcp`)

**Propósito**: Execução e comparação de backtests. ORQUESTRAÇÃO.

### Tools

| Tool | Descrição | Parâmetros |
|------|-----------|------------|
| `run_backtest` | Executa backtest | `symbol` (XAUUSD), `timeframe` (15), `days` (30), `label` |
| `compare_backtests` | Compara múltiplos backtests | `backtest_ids` (req) |
| `list_backtests` | Lista backtests realizados | `limit` (20) |
| `get_backtest_result` | Detalha um backtest | `backtest_id` (req) |

### Segurança
- Apenas opera em dados históricos
- Não envia ordens
- Não modifica configurações

---

## 4. Replay MCP (`leon-replay-mcp`)

**Propósito**: Reprodução e análise de operações passadas.

### Tools

| Tool | Descrição | Parâmetros |
|------|-----------|------------|
| `list_operations` | Lista operações registradas | `status`, `limit` (20), `days_back` (30) |
| `get_operation_detail` | Detalha operação | `operation_id` (req) |
| `analyze_operation` | Analisa resultado | `operation_id` (req) |
| `list_replays` | Lista replays disponíveis | `limit` (10) |
| `replay_operation` | Reproduz operação passo a passo | `operation_id` (req), `step_by_step` (true) |

### Segurança
- Apenas leitura de dados históricos
- Não modifica operações

---

## Protocolo MCP

Cada servidor implementa JSON-RPC 2.0 sobre stdio:

**Requisição**:
```json
{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_daily_context","arguments":{}},"id":1}
```

**Resposta**:
```json
{"jsonrpc":"2.0","result":{"content":[{"type":"text","text":"..."}]},"id":1}
```

**Métodos suportados**:
- `initialize` — Negociação de capacidades
- `tools/list` — Lista ferramentas disponíveis
- `tools/call` — Executa uma ferramenta
- `notifications/initialized` — Notificação de inicialização

**Códigos de erro**:
| Código | Significado |
|--------|-------------|
| -32700 | Parse error |
| -32600 | Invalid request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |

---

## Testes

Para testar um MCP manualmente:

```bash
# Testar Memory MCP
echo '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | python3 src/mcp/leon_memory_mcp.py

# Testar Market MCP
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"check_mt5_status","arguments":{}},"id":1}' | python3 src/mcp/leon_market_mcp.py
```

## Segurança

- Nenhum MCP envia ordens MT5
- Nenhum MCP modifica estratégia, risco, TP ou SL
- Nenhum MCP libera conta real
- Nenhum MCP remove guards
- Market MCP usa wrapper read-only (`_mt5_safe.py`)
- Memory MCP nunca sobrescreve arquivos existentes
- Backtest MCP só opera em dados históricos
- Replay MCP é somente leitura
