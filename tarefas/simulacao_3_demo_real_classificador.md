# Simulação 3 — Classificador DEMO/REAL

## Missão
Analise testes do classificador DEMO/REAL sem executar ordens.

## Classificação
TESTES / SEGURANÇA / OPERACIONAL LEON

## Agentes escolhidos
- Engineering Director (coordenação)
- QA Test Engineer (testes)
- Trading Systems Engineer (operacional)
- Security Engineer (segurança)

## Arquivos analisados
- `src/mt5_order_executor.py` (principal gate)
- `src/autonomy_guard.py`
- `src/execution_guard.py` (dead code)
- `src/decision_guard.py`
- `src/capital_protection.py` (dead code)
- `tests/test_agent_coordination.py`
- `tests/test_leon_operator_resilience.py`

## Riscos identificados

### Crítico
1. **Ponto único de falha** — A única verificação DEMO/REAL está na linha 720 de `mt5_order_executor.py`. Se `demo_only=false` no config.ini, todo o bloqueio é desabilitado.
2. **3 testes quebrados** em `test_agent_coordination.py` — Assertivas referenciam strings que não existem mais no código.

### Alto
3. **`execution_guard.py`, `discipline_guard.py`, `capital_protection.py` são dead code** — stubs sem lógica real, nunca importados.
4. **Nenhum teste para o gate principal** — linha 720-725 não tem cobertura.

### Médio
5. **3 padrões diferentes de leitura de config** — `demo_only` é parseado inconsistentemente.
6. **Sem campo de tipo de conta nos registros de ordem** — sem rastreabilidade forense.

## Conclusão
Sistema tem camadas de proteção mas depende de um único ponto. Dead code dá falsa sensação de segurança.

## Nenhuma alteração funcional realizada
Modo somente leitura respeitado.
