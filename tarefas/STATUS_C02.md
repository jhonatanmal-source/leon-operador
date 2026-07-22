# STATUS C02 — CORREÇÃO FINAL: REMOÇÃO DE sys.path GLOBAL

**Status:** APROVADO

---

## Por que sys.path.insert foi removido

A solução anterior inseriu `sys.path.insert(0, src_dir)` em `src/__init__.py` como contorno para que imports absolutos funcionassem no modo pacote. Essa mutação global do `sys.path` pode provocar:

- Colisões de nomes com módulos de terceiros;
- Módulos carregados com identidade dupla (`telegram_config` e `src.telegram_config`);
- Diferenças de comportamento entre ambiente de teste e produção;
- Dependência da ordem de inicialização.

## Solução adotada

**Imports relativos** em todos os módulos do pacote `src/` que importam outros módulos do mesmo pacote. O `src/__init__.py` foi restaurado para vazio (sem efeito colateral).

## Imports relativos aplicados

Todos os módulos que importam de irmãos dentro de `src/` foram convertidos de:

```python
from modulo_irmao import ...
```

para:

```python
from .modulo_irmao import ...
```

Isso inclui os 3 módulos alvo e toda a cadeia de dependências transitiva necessária para que `import src.telegram_engine`, `import src.operator_status` e `import src.leon_panel` funcionem sem `sys.path`.

## Compatibilidade preservada

O modo oficial passou a ser:

```python
import src.telegram_engine
import src.operator_status
import src.leon_panel
```

Testes que usavam `sys.path.insert(0, .../src)` + bare imports foram migrados para `import src.xxx` ou `from src.xxx import ...`.

## Módulos alterados

### src/ (imports relativos)

| Módulo | Alteração |
|--------|-----------|
| `src/telegram_engine.py` | `from .telegram_config import ...` |
| `src/operator_status.py` | `from .autonomy_guard`, `.emotion_engine`, `.telegram_config` |
| `src/leon_panel.py` | Todos os 22 imports convertidos para relativos |
| `src/brain_context_memory.py` | `from .operator_status import ...` |
| `src/collector_operator.py` | 4 imports relativos |
| `src/market_context_agent.py` | 4 imports relativos |
| `src/operator_council.py` | 5 imports relativos |
| `src/operation_readiness.py` | 2 imports relativos |
| `src/pre_operation_engine.py` | 2 imports relativos |
| `src/risk_control_agent.py` | `from .risk_method_engine import ...` |
| `src/telegram_alert.py` | 8 imports relativos |
| `src/system_watchdog_agent.py` | `from .autonomy_guard import ...` |
| `src/leon_operator.py` | ~20 imports relativos |
| `src/mt5_order_executor.py` | ~20 imports relativos |
| `src/emotion_filter.py` | `from .emotion_engine import ...` |
| `src/market_monitor.py` | 2 imports relativos |
| `src/operation_close_alert.py` | `from .telegram_engine import ...` |
| `src/candle_reader.py` | `from .candle_logger import ...` |
| `src/market_reader.py` | `from .price_logger import ...` |
| `src/mt5_operation_close_monitor.py` | `from .pre_operation_engine import ...` |
| `src/daily_operator_report.py` | `from .operation_report import ...` |
| `src/institutional_analysis_engine.py` | `from .elliott_study_engine import ...` |

### tests/ (migração de sys.path.insert)

| Teste | Alteração |
|-------|-----------|
| `tests/test_telegram_retry.py` | `sys.path.insert` removido; usa `import src.telegram_engine` |
| `tests/test_leon_operator_resilience.py` | `sys.path.insert` removido; usa `import src.leon_operator` |
| `tests/test_pre_operation_pipeline_consistency.py` | `sys.path.insert` removido; usa `import src.operator_council` |
| `tests/test_interest_zone_engine.py` | `sys.path.insert` removido; usa `from src.interest_zone_engine ...` |
| `tests/test_lab_entry_policy.py` | `sys.path.insert` removido; usa `import src.lab_entry_policy` |
| `tests/test_risk_context.py` | `sys.path.insert` removido; usa `import src.risk_control_agent` |
| `tests/test_timeframe_policy.py` | `sys.path.insert` removido; usa `from src.timeframe_policy ...` |
| `tests/test_agent_coordination.py` | `sys.path.insert` removido; imports convertidos nas funções |
| `tests/test_mt5_order_executor.py` | `sys.path.insert` removido (desnecessário) |
| `tests/test_web_active_errors.py` | `sys.path.insert` removido (desnecessário) |

### Arquivos criados

| Arquivo | Conteúdo |
|---------|----------|
| `tests/test_telegram_engine.py` | 28 testes de telegram (import, config, fail-safe, identidade, subprocesso) |

## Testes antes e depois

| Métrica | Antes | Depois |
|---------|-------|--------|
| Total passed | 138 | 166 |
| Total failed (pré-existentes) | 3 | 3 |
| Telegram tests | 7 | 35 |
| Import `src.telegram_engine` | ❌ Falhava | ✅ Funciona |
| Import `src.operator_status` | ❌ Falhava | ✅ Funciona |
| Import `src.leon_panel` | ❌ Falhava | ✅ Funciona |

Os 3 failures pré-existentes são em `test_risk_control_agent.py` (não relacionados).

## Evidência de identidade única

Teste `test_identity_unica_apos_import_pacote` verifica que:
- `sys.modules` contém apenas `src.telegram_config` (nunca `telegram_config` como top-level);
- Nenhuma identidade dupla para o mesmo arquivo físico.

## Evidência de import de diretório diferente

Teste subprocesso (`TestImportDeDiretorioDiferente`) executa a partir de um processo filho:
```python
sys.path.insert(0, '/opt/leon/app')
import src.telegram_engine
import src.operator_status
```
Ambos retornam código de saída zero.

## Evidência de ausência de HTTP real

- Todos os 35 testes de telegram usam `patch.object(eng.requests, "post", ...)`.
- Teste `test_nenhuma_chamada_real_internet` verifica explicitamente que `requests.post` mockado nunca atinge a rede.
- Teste `test_nenhuma_chamada_mt5` verifica que `order_send` não está presente no módulo.

## Pendências

Nenhuma.
