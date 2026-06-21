# Auditoria Geral do Sistema - 2026-06-19

## Resumo executivo

- O sistema possui boa separação entre operador, memória, painel web e monitoramento.
- A base de permissões do painel já era razoável, mas havia um risco crítico de segurança no bootstrap do administrador.
- Havia duplicidade entre o painel legado do Leon e o painel web remoto, o que aumentava complexidade operacional.
- A interface web apresentava textos com encoding corrompido, reduzindo clareza e profissionalismo.

## Riscos identificados

1. Crítico: senha inicial do administrador fixa em código e exposta na tela de login.
2. Alto: segredo sensível em `config.ini`, inclusive integração externa em texto puro.
3. Médio: dois painéis paralelos com papéis parecidos, elevando chance de confusão operacional.
4. Médio: logs e saúde do sistema espalhados, dificultando leitura remota por colaborador.
5. Baixo: vários textos com caracteres corrompidos, afetando usabilidade.

## Melhorias aplicadas nesta rodada

- Bootstrap do admin passou a usar senha gerada via `.env` ou arquivo local de bootstrap fora do Git.
- Tela de login deixou de exibir senha padrão fixa.
- Novo `Painel Leon` unificado dentro do painel web.
- Modo visualização explícito para `COLABORADOR` e `VISUALIZADOR`.
- Página de saúde e telas principais reescritas com textos limpos.
- Script e mensagens de acesso remoto atualizados para o fluxo unificado.

## Recomendações para próxima etapa

1. Mover token do Telegram e demais segredos totalmente para `.env`, removendo-os do `config.ini`.
2. Criar rotação formal de segredos administrativos.
3. Adicionar testes automatizados para login, permissões e rotas do painel.
4. Considerar descontinuar o painel legado remoto, mantendo-o apenas como ferramenta local.
5. Adicionar trilha de auditoria também para visualização de análises, não só login e revisão.
