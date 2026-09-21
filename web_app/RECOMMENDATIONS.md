# LEON WEB COLLAB — Melhorias Recomendadas

**Data:** 2026-07-20
**Arquivos analisados:** `leon_panel.html`, `dashboard.html`, `base.html`, `style.css`, `system_health_service.py`, `leon_routes.py`

---

## 1. PAINEL LEON (`leon_panel.html`)

### 1.1 Status dos agentes — visual confuso
- Cards de status usam apenas cores (verde/vermelho/amarelo) sem ícones
- **Sugestão:** Adicionar ícones SVG ou unicode (✓, ✗, ⏳) para melhorar acessibilidade
- **Impacto:** Usuários com daltonismo não conseguem distinguir status

### 1.2 Grid de stats — 5 colunas em linha
- `stats-grid` usa `repeat(5, 1fr)` — em telas médias (900-1200px) os cards ficam apertados
- **Sugestão:** Usar `repeat(auto-fit, minmax(160px, 1fr))` para layout flexível
- **Local:** `style.css:113-117`

### 1.3 Health grid — 2 colunas sempre
- `health-grid` é fixo em 2 colunas, mas em mobile vira 1 coluna abruptamente
- **Sugestão:** Adicionar breakpoint intermediário (620-900px) com 1 coluna

### 1.4 Log box — sem filtro ou busca
- `pre.log-box` mostra logs brutos sem possibilidade de busca
- **Sugestão:** Adicionar campo de filtro/filtro por nível (ERROR, WARNING, INFO)

### 1.5 Tabela de acessos — sem paginação
- Mostra apenas 12 registros sem opção de ver mais
- **Sugestão:** Adicionar botão "Carregar mais" ou paginação simples

### 1.6 Dados ausentes no template
- `panel.mt5_monitor.status` é exibido mas não há seção dedicada ao MT5
- `panel.shadow` (shadow_trades) não é exibido no template
- `panel.risk_methods` (desempenho por método) não é exibido
- `panel.top_down` não é exibido
- `panel.market_context` não é exibido
- **Sugestão:** Criar seções dedicadas para cada um desses dados

---

## 2. DASHBOARD (`dashboard.html`)

### 2.1 Stats incompletos
- Mostra Total, Pendentes, Aprovadas, Rejeitadas — mas não mostra taxa de acerto
- **Sugestão:** Adicionar card "Taxa de acerto" (% aprovadas / total)

### 2.2 Tabela de análises — sem ordenação
- Tabela não permite ordenar por coluna
- **Sugestão:** Adicionar JavaScript para ordenação por clique no header

### 2.3 Sem indicador de carregamento
- Não há feedback visual durante carregamento de dados
- **Sugestão:** Adicionar skeleton loading ou spinner

---

## 3. BASE (`base.html`)

### 3.1 Topbar — sem responsividade adequate
- Em mobile, a nav vira horizontal scrollável mas os links ficam pequenos
- **Sugestão:** Usar menu hamburger em telas < 620px

### 3.2 Sem favicon
- Não há `<link rel="icon">` definido
- **Sugestão:** Adicionar favicon.ico ou SVG

### 3.3 Sem meta tags SEO
- Falta `<meta name="description">`, Open Graph tags
- **Sugestão:** Adicionar meta tags básicas

### 3.4 Sem service worker / PWA
- Painel pode ser instalado como app
- **Sugestão:** Considerar manifest.json + service worker para uso offline

---

## 4. CSS (`style.css`)

### 4.1 Variáveis CSS incompletas
- Usa `--gold`, `--green`, `--red`, `--blue` mas não define `--yellow` para badges
- Badge `.pendente` usa `color: #f3df9d` inline em vez de variável
- **Sugestão:** Criar `--yellow` e usar consistentemente

### 4.2 Sombras inconsistentes
- Cards usam `box-shadow: 0 18px 45px rgba(0,0,0,0.18)` — muito pesado
- **Sugestão:** Reduzir para `0 8px 24px rgba(0,0,0,0.12)` para efeito mais sutil

### 4.3 Transições ausentes
- Hover states não têm transição suave
- **Sugestão:** Adicionar `transition: all 0.2s ease` nos elementos interativos

### 4.4 Dark mode — sem prefers-color-scheme
- Modo escuro é forçado, sem opção de modo claro
- **Sugestão:** Adicionar `@media (prefers-color-scheme: light)` como alternativa

### 4.5 Scrollbar customizada
- Log boxes usam scrollbar padrão do sistema
- **Sugestão:** Customizar scrollbar com `::-webkit-scrollbar` para combinar com tema

---

## 5. BACKEND (`system_health_service.py`)

### 5.1 Import duplicado
- Linha 1-2: `import configparser` aparece duas vezes
- **Ação:** Remover duplicata

### 5.2 Process detection — frágil
- `_process_running()` usa substring match em CommandLine
- Pode dar falso positivo se outro processo tiver fragmento similar
- **Sugestão:** Usar regex mais específica ou verificar nome do executável

### 5.3 Sem cache de dados
- Cada request ao painel re-executa todas as funções de coleta
- `_mt5_status()` inicializa e desliga MT5 a cada chamada
- **Sugestão:** Adicionar cache de 30-60 segundos para dados que não mudam rápido

### 5.4 Erros não tratados
- `_mt5_status()` pode falhar se MT5 estiver corrompido
- `_remote_status()` pode falhar se cloudflared não existir
- **Sugestão:** Adicionar try/except mais granular com fallback

### 5.5 Sem logs estruturados
- Usa `print()` ou arquivos de texto para logs
- **Sugestão:** Usar `logging` module com formato JSON para facilitar análise

---

## 6. SEGURANÇA

### 6.1 CSRF token em formulário
- Formulário de troca de senha usa `csrf_token()` — correto
- Mas formulários de logout e outros não verificam explicitamente
- **Sugestão:** Garantir que todas as rotas POST tenham validação CSRF

### 6.2 Session cookies
- `SESSION_COOKIE_SECURE=config.SESSION_COOKIE_SECURE` — depende da config
- **Sugestão:** Forçar `Secure=True` em produção

### 6.3 Sem Content Security Policy
- Não há CSP headers definidos
- **Sugestão:** Adicionar `Content-Security-Policy` header

---

## 7. PERFORMANCE

### 7.1 Sem compressão gzip
- Respostas não são comprimidas
- **Sugestão:** Adicionar middleware de compressão (Flask-Compress)

### 7.2 Sem lazy loading
- Imagens e componentes pesados carregam imediatamente
- **Sugestão:** Usar `loading="lazy"` em imagens

### 7.3 JavaScript não minificado
- `virtual_operations.js` pode ser minificado
- **Sugestão:** Usar ferramentas como Terser para produção

---

## 8. PRIORIDADES

| # | Melhoria | Impacto | Esforço |
|---|----------|---------|---------|
| 1 | Remover import duplicado em `system_health_service.py` | Baixo | Trivial |
| 2 | Adicionar ícones nos status cards | Alto | Baixo |
| 3 | Usar grid responsivo `auto-fit` no stats-grid | Médio | Baixo |
| 4 | Adicionar cache de 30s para dados do painel | Alto | Médio |
| 5 | Criar seções para shadow_trades, risk_methods, top_down | Alto | Médio |
| 6 | Adicionar menu hamburger em mobile | Médio | Médio |
| 7 | Adicionar filtro de busca nos logs | Alto | Médio |
| 8 | Customizar scrollbar nos log boxes | Baixo | Baixo |
| 9 | Adicionar transições CSS nos hovers | Baixo | Trivial |
| 10 | Adicionar CSP headers | Alto | Médio |

---

*Arquivo gerado automaticamente para revisão do painel web.*
