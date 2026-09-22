# LEON - LEIA PRIMEIRO AO RETOMAR

Atualizado em 22/09/2026. Este documento e um ponto de continuidade, nao prova de estado atual. Confirmar servicos, conta, configuracao e resultados antes de agir. Uma nova instrucao explicita do usuario prevalece sobre este resumo.

## Acesso e locais

- VPS: 184.107.88.153. Projeto ativo: /opt/leon/app. Python: /opt/leon/venv/bin/python.
- Acesso pelo PowerShell: ssh -i "$env:USERPROFILE\.ssh\id_ed25519_leon_vps" root@184.107.88.153
- Arquivos pertencem ao usuario leon. O acesso GitHub esta configurado para leon, nao para root. Usar sudo -u leon -H para comandos Git remotos. Nao desativar verificacao SSH.
- Workspace PC: C:/Users/Casa/Documents/Codex/2026-09-07/acesse.
- Backup PC: C:/Users/Casa/Documents/LEON-Backups/20260921-135100.
- Nenhuma senha, token, chave privada ou numero de conta deve ser colocado neste documento ou publicado no GitHub.

## Pedido e regras vigentes

- Operador de day trade em DEMO. Execucao real permanece bloqueada; este documento nao autoriza altera-la.
- Elliott fornece contexto/direcao em varios tempos. SMC decide entradas. Operar retomadas e correcoes confirmadas; nao restringir tudo a uma unica direcao.
- FVG nao e obrigatorio universalmente. Nao inventar gatilho nem remover confirmacoes para aumentar quantidade de ordens.
- Risco configurado de referencia: 0,5% por ordem, ate 3 posicoes abertas e 1,5% de risco aberto. Conferir config atual antes de citar.
- SEM limite diario por quantidade de entradas. Stop diario 2%; protecoes da mesa preservadas.
- Protecao de devolucao: lucro FECHADO acima de 4% da base diaria da conta arma parada ao devolver 50% do pico de lucro fechado. Base deve acompanhar a conta/dia, nao ser valor fixo universal.
- Stop e alvo tecnicos; o usuario pediu fechamento por SL/TP, nao trailing improvisado.
- Em 21/09 o usuario autorizou autonomia DEMO ate desligamento manual. Estado usa until_revoked=true; /autonomy off revoga. Nao reativar se usuario desligou. Revogacao deve sobreviver a reinicio.
- Trechos antigos de AGENTS.md e CONTEXTO_EVOLUCAO.md sobre '3 trades por dia' e somente uma direcao sao historicos e foram superados pelos pedidos acima. Nao restaura-los por engano.

## O que foi publicado

1. Setup elliott-multidegree-smc-entry-v2.8: zonas estruturais, reteste prospectivo, entradas por Order Block e CHOCH + Order Block; Elliott como contexto.
2. Em 19/09: reserva de regiao impede pre-operacoes concorrentes/duplicadas e preserva proprietario durante atualizacao da zona. Lock entre processos.
3. Em 21/09: autonomia ate revogacao e motivo AUTONOMY_REVOKED para impedir reativacao automatica no startup.
4. Aprendizado smc_opportunity_v1: agrupa ativo/direcao/modelo SMC/contexto, sem fragmentar por nome de onda. Conta/regiao e uma oportunidade; tickets e PnL originais preservados.
5. Abaixo de 4 oportunidades independentes por grupo, score neutro, SEM bloquear setup valido. Acima disso ranking exploratorio regularizado n/(n+20). Nao e probabilidade calibrada nem vantagem validada.
6. Comparacao entre escolhido e candidato valido mais recente registrada em metadados de ordem e resultado fechado. Relatorios separam observacoes, memoria antiga, tickets e oportunidades.
7. Coletor de qualidade independente: leon-quality.timer a cada 5 minutos, ate 2 posicoes fechadas por execucao, ate 6 paginas de 10.000 ticks, ate 3 tentativas. Somente leitura no MT5.
8. Mede MFE/MAE, spread, custos, preco executado e desvio do solicitado; bid para compra e ask para venda, horarios numericos UTC do broker. Cotacoes incompletas sinalizadas; dados ausentes nao viram zero.
9. Avaliacao prospectiva separa escolhas alteradas/mantidas. Nao conhece o lucro das alternativas nao executadas e nao comprova causalidade.

## Arquivos principais

- src/autonomy_guard.py, src/telegram_commands_mcp.py: autonomia e comandos.
- src/interest_zone_engine.py, src/pre_operation_engine.py: identidade/reserva das regioes.
- src/opportunity_learning.py, src/operational_evidence.py: agrupamento, estatisticas e evidencias.
- src/mt5_order_executor.py: selecao e registro da decisao; guards preservados.
- src/mt5_operation_close_monitor.py: resultado fechado reconciliado com broker.
- src/trade_quality.py, src/quality_collector.py, src/learning_evaluation.py: medicao e avaliacao.
- src/daily_learning_report.py: consolidacao diaria; horario observado 23h.
- data/confirmed_mt5_outcomes.json: resultados confirmados. Nao inserir simulacoes nem editar perdas.
- data/order_evidence/, data/trade_quality/, data/quality_collector_status.json, data/latest_learning_selection.json: evidencias operacionais privadas.
- data/operator_heartbeat.json, data/latest_setup_decision.json: estado e bloqueios atuais.

## Evidencia na ultima revisao

- Entre 16 e 21/09: 7 operacoes, 5 oportunidades, 3 grupos. Um ganho e seis perdas, liquido +USD 176,26. Um unico ganho de USD 487,06 sustentou o saldo positivo. Nao demonstra consistencia.
- Grupos: compra OB/tendencia = 2 oportunidades; compra CHOCH OB/tendencia = 1; venda OB/correcao = 2. Nenhum grupo tinha 4; ranking ainda neutro.
- Medicoes iniciais: venda ticket 546233816 teve MFE observado 10,34R e MAE 0,27R; compra 546657317 teve MFE 0 e MAE 1,02R. Sao movimentos de preco, nao lucro realizavel.
- Historico do replay de 60 dias v2.8: 54 trades, 13 ganhos, -8,1441R, fator de lucro 0,806. Nao ocultar o resultado negativo nem confundir conserto de software com melhora estatistica.
- Ultima consulta registrada: 21/09 20:36, PAUSA_MERCADO. Reconsultar; nao assumir operador travado, rodando ou lucrativo a partir deste snapshot.

## Testes e limites

- 215 testes e 3 subtestes focados passaram antes da ultima entrega; nenhum teste enviou ordens.
- As 2 falhas e 17 erros de fixtures anteriores foram corrigidos em 22/09. Ver a entrega abaixo e seus limites; nao afirmar sucesso total da suite.
- Aba Aprendizado do painel entregue em 22/09. Pende validacao independente da melhora. Nao ha 'consciencia' humana nem comprovacao de aprendizado que gera lucro.
- Videos nao foram todos assistidos/analisados integralmente; parte das transcricoes veio traduzida de forma duvidosa. Nao alegar estudo completo do material.
- Ha pesquisas/alteracoes locais NAO publicadas em work/remote_leon (inclusive sweep_reclaim_model e outros experimentos). Nunca substituir a VPS por essa pasta inteira. As entregas recentes foram preparadas em work/learning_release e work/quality_release a partir do codigo vivo.

## Backups e GitHub

- Repositorio: https://github.com/jhonatanmal-source/leon-operador
- Branch de backup publicado: backup/2026-09-21. Commit de codigo: 6171fe48cbfc9ed1bd9daba8782ce0886342634d.
- Checkout sanitizado do backup: /home/leon/backup-github-20260921. O checkout vivo /opt/leon/app continua em fix/simbolo-entrada com alteracoes nao commitadas. NAO resetar nem dar checkout para alinhar isso.
- Backup GitHub exclui credenciais, bancos e dados privados. Seis arquivos foram omitidos por verificacao conservadora; ver BACKUP-NOTES.md. Nao e uma imagem completa de restauracao.
- Backup completo de arquivos: /opt/leon/backups/manual-20260921-135100/projeto-vps.tar.gz. Captura com servicos ativos, nao snapshot transacional de bancos.
- Backups de mudancas: /opt/leon/backups/zone-reservation-20260919-230858; /opt/leon/backups/autonomy-until-revoked-20260921-174840; /opt/leon/backups/opportunity-learning-20260921-180533; /opt/leon/backups/quality-20260921-191015.
- PC: arquivos-locais-em-andamento.tar.gz, projeto-vps.tar.gz e leon-published-6171fe4.tar.gz na pasta de backup acima. Preservar os tres; conteudos diferentes.

## Como retomar com seguranca

1. Ler este arquivo, AGENTS.md, tarefas/agent_lock.json, tarefas/handoff_atual.md e contexto/registro diario.
2. Conferir data e servicos: leon-operator, leon-mt5, leon-rpyc, leon-telegram-bot, leon-web e leon-quality.timer. O leon-quality.service e oneshot: ficar inativo apos concluir com sucesso e normal.
3. Ler heartbeat, autonomia, decisao e evidencias atuais sem imprimir credenciais. Confirmar conta DEMO antes de qualquer mudanca operacional.
4. Comparar codigo vivo e hashes antes de editar. Usar exclusao mutua tarefas/.agent_lock_mutex e registrar escritor em agent_lock.json. Nao sobrepor outro agente.
5. Fazer backup e testar em copia isolada. Nao executar a suite diretamente sobre dados vivos nem enviar ordens de teste.
6. Publicar somente arquivos revisados, reiniciar apenas servicos necessarios, verificar heartbeat e resultados. Atualizar handoff, este documento e registro diario; liberar lock.
7. Buscar falhas comprovadas e novas evidencias. Nao reduzir protecoes nem forcar entradas para fabricar aprendizado.

Mensagem para uma nova conversa: 'Acesse a VPS e leia /opt/leon/app/CONTINUIDADE-LEON.md e o handoff antes de continuar. Confira o estado atual; nao altere risco ou autonomia sem meu pedido.'


## Panel and permission diagnosis 2026-09-22
- Account reported trade_allowed=false while terminal connected, algo enabled and symbol trade_mode=4. This is an account permission block, not proof of market closure. No credentials changed; user plans new demo login.
- CONTA_SEM_PERMISSAO distinguishes account permission, PAUSA_MERCADO quote pause, FALHA_TECNICA connection/symbol issues. Telegram and panel preserve exact reason; demo autonomy metadata retained during pauses.
- Central Virtual Aprendizado tab: confirmed closes, independent opportunities, group ranking, MFE/MAE with incomplete coverage, filters, indefinite autonomy label. No fake agent activity. Desktop/mobile preview verified; no horizontal document overflow at 390px.
- 258 focused tests plus 3 subtests pass in network-isolated staging. Repaired original legacy fixtures and learning-contract fixtures. Full discovery is NOT all-green: test_leon_brain.py exits during collection; identity suite needs its migration script and alert-fixture review.
- Risk, account settings, autonomy state, stop/targets and trading strategy unchanged. No test orders.
- Video review remains incomplete; prospective improvement requires future evidence. No new profitability claim.
- Backup: /opt/leon/backups/panel-permissions-20260922-061142
