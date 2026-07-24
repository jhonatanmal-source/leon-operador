# Testes — Memory Context Engine

## Status: PENDENTE (shadow mode ativo)

### Testes a implementar (tests/test_memory_context.py)
- [ ] consulta com contexto valido
- [ ] busca de memorias semelhantes
- [ ] tempo de resposta < 500ms
- [ ] Vault indisponivel (fallback)
- [ ] memoria corrompida
- [ ] contexto vazio
- [ ] contexto semelhante parcial
- [ ] isolamento do executor MT5 (nao envia ordens)
- [ ] shadow mode bloqueia registro de eventos operacionais

### Como ativar testes
```bash
cd /opt/leon/app && python3 -m pytest tests/test_memory_context.py -v
```
EOF
