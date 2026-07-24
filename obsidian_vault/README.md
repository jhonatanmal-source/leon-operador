# LEON XAU ELITE AI — Vault Obsidian

Este vault serve como memória auxiliar do LEON, complementando o sistema de aprendizado diário.

## Estrutura

```
obsidian_vault/
├── LEON XAU ELITE AI.md          # Página principal
├── aprendizados_diarios/          # Sincronizado com tarefas/aprendizados_diarios/
│   ├── CONTEXTO_EVOLUCAO.md      # Compilado de aprendizados
│   ├── INDICE.md                  # Índice de entradas
│   └── YYYY-MM-DD.md             # Aprendizados do dia
├── operacional/                   # Documentação operacional
├── analise/                       # Análises de mercado
├── referencias/                   # Links e materiais de estudo
└── reunioes/                      # Atas e decisões
```

## Sincronização

Use o script `scripts/sync_obsidian_vault.sh` para sincronizar o vault com o sistema de aprendizado diário:

```bash
./scripts/sync_obsidian_vault.sh          # sincroniza
./scripts/sync_obsidian_vault.sh status   # verifica status
```

## Acesso

- **CLI**: `npx ob` (obsidian-headless) para gerenciar vault
- **Editor**: qualquer editor de texto (VS Code, vim, etc.)
- **Obsidian Desktop**: abra a pasta `obsidian_vault/` como vault

## Regras

- Não armazenar credenciais, tokens ou senhas
- Não armazenar números de conta real
- Não armazenar informações pessoais
- Sincronizar aprendizado diário antes de iniciar missões
