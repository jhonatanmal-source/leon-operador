# Mecanismo Automático de Salvamento de Aprendizados

## 1. Visão Geral — Como o Mecanismo Funciona

O LEON XAU ELITE AI possui um sistema de aprendizado diário que captura automaticamente o conhecimento gerado durante cada missão (execução, testes, correções, decisões operacionais). O mecanismo funciona da seguinte forma:

- **Gatilho automático**: Ao final de cada missão (seja bem-sucedida, interrompida ou com erro), o sistema dispara o salvamento estruturado dos aprendizados em arquivos Markdown padronizados.
- **Agregação por data**: Todos os aprendizados do dia são consolidados em um único arquivo `YYYY-MM-DD.md` na pasta `tarefas/aprendizados_diarios/`.
- **Promoção inteligente**: Padrões recorrentes, decisões estruturais ou erros críticos são automaticamente promovidos para o arquivo `CONTEXTO_EVOLUCAO.md`, que serve como referência rápida para todos os agentes no início de novas missões.
- **Integração com vault Obsidian**: Os arquivos são mantidos em sincronia bilateral com o vault Obsidian via script `scripts/sync_obsidian_vault.sh`, garantindo que o conhecimento esteja disponível tanto no ambiente de código quanto na documentação pessoal da equipe.
- **Registro de segurança**: O sistema impede automaticamente o salvamento de credenciais, tokens, números de conta real ou qualquer dado sensível, aplicando filtros de segurança antes da persistência.

O objetivo é garantir que nenhum aprendizado valioso se perca ao final de uma missão, ao mesmo tempo em que se mantém a segurança operacional como prioridade absoluta.

---

## 2. Estrutura de Arquivos — Onde os Aprendizados São Salvos

A pasta de aprendizados tem a seguinte estrutura organizada:

```
tarefas/aprendizados_diarios/
├── CONTEXTO_EVOLUCAO.md          # ← Padrões acumulados, decisões estruturais, erros recorrentes
├── INDICE.md                     # ← Índice geral com data e resumo de cada entrada
├── README.md                     # ← Regras rápidas e instruções de sincronização
├── YYYY-MM-DD.md                 # ← Aprendizados do dia (um por data)
└── (outros arquivos de suporte)
```

### Arquivos de entrada diária

Cada arquivo `YYYY-MM-DD.md` segue o modelo abaixo:

```markdown
# Aprendizados Diários — YYYY-MM-DD

## Correcao
- Descrição do erro encontrado e como foi resolvido.

## [Outra categoria]
- Detalhes da operação, decisão ou padrão identificado.

## Backup dedicado dos dados operacionais implantado
- Descrição de melhoria de infraestrutura ou processo.

## [Outra seção]
- Contexto adicional, validações ou verificadores (padrões a adotar).
```

### Arquivo de contexto acumulado

`CONTEXTO_EVOLUCAO.md` contém seções organizadas:

- **Padrões Identificados** — padrões de código, arquitetura, configuração que se repetem e devem ser conhecidos por todos os agentes.
- **Decisões Estruturais** — decisões de design tomadas durante o desenvolvimento que afetam o comportamento do sistema.
- **Erros Recorrentes** — erros que apareceram mais de uma vez, com causas raiz e verificadores para evitar regressão.
- **Correções Aplicadas (Histórico)** — tabela cronológica de correções já aplicadas, com data, arquivo e descrição.

### Índice

`INDICE.md` mantém uma tabela simples:

| Data | Resumo |
|------|--------|
| 2026-07-22 | Aprendizados Diários — 2026-07-22 |
| 2026-07-23 | Aprendizados Diários — 2026-07-23 |
| ...  | ... |

---

## 3. O Que é Capturado em Cada Checkpoint de Missão

No final de cada missão, o sistema captura automaticamente as seguintes informações, organizadas por categoria:

### Operações / Missões Executadas
- Nome ou ID da missão
- Status final (concluída, interrompida, com erro)
- Tempo de duração
- Resultado principal (ex.: "TEST-000001: operação de teste fechada WIN_TP1")

### Decisões Tomadas
- Decisões estratégicas ou operacionais tomadas durante a missão
- Escolhas entre opções alternativas (ex.: "escopo A + C — sem B (instrumentação)")
- Justificativa da decisão

### Erros Encontrados
- Descrição do erro ou problema encontrado
- Causa raiz (se conhecida)
- Impacto operacional
- Como o erro foi resolvido ou contornado

### Correções Aplicadas
- Alterações de código ou configuração feitas durante a missão
- Arquivos modificados e o motivo da mudança
- Commit hash ou identificador da correção (se aplicável)

### Padrões Identificados
- Padrões de comportamento, configuração ou operação observados
- Padrões que valem como "verificador" para agentes futuros
- Exemplos de sucesso ou falha que se repetem

### Recomendações para Outros Agentes
- Avisos, recomendações ou restrições para agentes que trabalharem em áreas similares
- Dependências entre tarefas ou pendências abertas

### Contexto Adicional
- Qualquer outra informação relevante que não se encaixe nas categorias acima, mas que seja útil para a equipe

---

## 4. Como o Sistema Garante que Nenhum Dado Sensível é Capturado

A segurança é aplicada em múltiplas camadas antes de qualquer aprendizado ser persistido:

### Filtros Automáticos de Conteúdo
- O sistema verifica o texto em busca de padrões que indiquem dados sensíveis antes de salvar.
- **Bloqueado explicitamente**: números de conta MT5 (padrões como `Gold_Spot`, `XAUUSD`, contas numéricas longas), tokens de API, chaves privadas, senhas.
- **Endereços e identificadores**: URLs completas, caminhos de sistema que contenham dados de usuários, IDs de chat sensíveis.

### Regras de Redação Obrigatória
- Se um aprendizado contiver acidentalmente um dado sensível, o sistema:
  1. Remove ou mascara o dado automaticamente.
  2. Registra um aviso no log de operação: "Sensitive data filtered from learning entry".
  3. Marca a entrada com a categoria ` filtrado` para rastreabilidade.

### Proibição Manual Rigorosa
- **Nenhum agente** pode forçar o salvamento de dados que o sistema tenha bloqueado.
- Se um agente precisar registrar informações sensíveis, deve fazê-lo **fora** do sistema de aprendizado diário (ex.: vault Obsidian privado, documento criptografado) e registrar apenas o aprendizado não-sensível no sistema oficial.
- O sistema lança erro se detectar tentativa de bypass dos filtros de segurança.

### Auditoria Contínua
- O arquivo `CONTEXTO_EVOLUCAO.md` contém uma seção de "Contratos Protegidos" que relembra as regras absolutamente proibidas (conta real bloqueada, nenhum agente pode enviar ordens MT5, etc.).
- Qualquer violação dessas regras é imediatamente sinalizada e o aprendizado correspondente é removido.

---

## 5. Interação dos Agentes com o Novo Sistema

### Fluxo Padrão (Automático)
- No **início** de cada missão, o agente carrega automaticamente `CONTEXTO_EVOLUCAO.md` e o arquivo do dia atual (`tarefas/aprendizados_diarios/YYYY-MM-DD.md`).
- No **fim** de cada missão, o agente registra os aprendizados usando a skill `leon-daily-learning` — não há necessidade de execução manual se o fluxo for seguido corretamente.

### Override Manual (Quando Necessário)
Em casos excepcionais, um agente pode precisar interagir manualmente:

1. **Adicionar aprendizado não coberto automaticamente**:
   - Se o agente identificar um aprendizado que o sistema automático não capturou (ex.: decisão estratégica de alto nível), pode editar manualmente o arquivo `YYYY-MM-DD.md` adicionando as seções correspondentes.
   - Use o mesmo formato dos demais arquivos para consistência.

2. **Promover manualmente um padrão para CONTEXTO_EVOLUCAO.md**:
   - Se um padrão for identificado como recorrente ou estrutural, o agente deve adicioná-lo ao final do arquivo `CONTEXTO_EVOLUCAO.md` na seção apropriada (Padrões Identificados, Decisões Estruturais ou Erros Recorrentes).
   - O agente deve seguir o formato já existente no arquivo (vírgulas negritadas, tabelas, etc.).

3. **Interromper e reiniciar o salvamento**:
   - Se a missão for interrompida inesperadamente (crash, perda de conexão), o sistema tenta salvar o que foi coletado até o momento.
   - O agente pode retomar o salvamento a partir do checkpoint mais recente ao reiniciar a missão (ver tópico "Como lidar com interrupções de missão").

### Pontos de Atenção
- **Nunca** remova ou altere entradas de outros agentes nos arquivos diários.
- **Sempre** verifique se o aprendizado não contém dados sensíveis antes de salvar manualmente.
- **Mantenha o INDICE.md atualizado** sempre que adicionar um novo arquivo de data.

---

## 6. Como Promover Padrões para CONTEXTO_EVOLUCAO.md

Padrões são promovidos do aprendizado diário para o contexto acumulado quando atendem a critérios de relevância estrutural. O processo é:

### Critérios de Promoção
- O padrão apareceu em **múltiplas missões** ou foi crítico em uma missão de alta relevância.
- O padrão envolve **decisões de design** que afetam o comportamento do sistema ou a operação de agentes futuros.
- O padrão é um **erro recorrente** que, se não documentado, causaria regressão.
- O padrão envolve **configurações de segurança, guards ou restrições** que todos os agentes devem respeitar.

### Procedimento de Promoção
1. **Identifique o padrão** no arquivo `YYYY-MM-DD.md` do dia.
2. **Acesse** `CONTEXTO_EVOLUCAO.md` e localize a seção apropriada (Padrões Identificados, Decisões Estruturais ou Erros Recorrentes).
3. **Adicione a entrada** seguindo o formato existente:
   - Use negrito para o nome do padrão ou da área (ex.: `- **Web App**: `web_app/services/` ...`).
   - Se for um erro recorrente, inclua a data da primeira ocorrência e, se possível, a correção aplicada.
   - Se for um padrão de código, relate o local do arquivo e a lição aprendida.
4. **Atualize o INDICE.md** adicionando o novo padrão ao rodapé ou reorganizando a tabela se necessário.
5. **Registre a promoção** como um aprendizado adicional no próprio dia, indicando que o padrão foi promovido.

### Exemplo de Promoção

```markdown
## Padrões Identificados
- **Web App**: Templates Flask usam exclusivamente `{{ }}` com auto-escaping — sem `|safe` ou `autoescape false`
- **MT5 health cache TTL 30s**: Cache com `threading.Lock()` e `time.monotonic()` no health check. Evita `mt5.initialize()` + `mt5.shutdown()` a cada requisição HTTP.
```

---

## 7. Como Lidar com Interrupções de Missão

Cenários de interrupção são tratados da seguinte maneira:

### Interrupção Detectada pelo Sistema
- Se a missão for interrompida (crash, timeout, perda de conexão MT5), o sistema tenta salvar automaticamente o que foi coletado até o momento.
- O arquivo `YYYY-MM-DD.md` pode estar incompleto — as seções que estavam sendo processadas são salvas com o que havia até o ponto da interrupção.
- Ao reiniciar a missão, o agente deve carregar o arquivo existente e adicionar as informações que faltaram.

### Retomada Manual (Checkpoint)
1. **Verifique o último arquivo de data**: carregue `tarefas/aprendizados_diarios/YYYY-MM-DD.md` — ele conterá o que foi salvo até a interrupção.
2. **Rode o comando `/leon-aprender`** para consolidar aprendizados da equipe e garantir que o contexto acumulado esteja atualizado.
3. **Complete as seções faltantes** manualmente, seguindo o formato padrão.
4. **Promova padrões críticos** para `CONTEXTO_EVOLUCAO.md` se ainda não tenham sido promovidos.
5. **Atualize o INDICE.md** se novos arquivos foram criados ou se o resumo mudou.

### Cenário: Missão Interrompida Antes do Fim do Dia
- Se a missão for interrompida antes do fim do dia calendário, o arquivo do dia em andamento deve ser tratado como "rascunho incompleto".
- Ao retomar, o agente deve:
  1. LER o arquivo existente (`tarefas/aprendizados_diarios/YYYY-MM-DD.md`).
  2. ADICIONAR as seções que ainda não foram registradas, marcando claramente como "continuação da missão interrompida".
  3. SALVAR o arquivo concluído.
  4. O sistema considerará o novo aprendizado como parte do mesmo dia (mesma data).

### Prevenção
- O sistema emite um aviso se detectar que um arquivo diário tem menos de 3 categorias preenchidas, indicando possível interrupção prematura.
- Recomenda-se que agentes façam um "checkpoint mental" a cada 2 horas de missão, anotando mentalmente os principais aprendizados que serão registrados no final.

---

## Histórico de Revisão

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-08-31 | 1.0 | Documentação inicial do mecanismo automático de salvamento de aprendizados |

---