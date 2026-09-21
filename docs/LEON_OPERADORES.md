# LEON XAU AI - Operadores Principais

Este documento define a arquitetura operacional do LEON XAU AI.

O LEON e um agente de estudo e analise do XAUUSD. Ele aprende diariamente com o mercado, registra memoria, observa estatisticas e respeita a protecao de risco antes de qualquer decisao operacional.

## 1. Operador Coletor

Nome: Market Collector

Missao:
- Ler MT5.
- Coletar candles.
- Coletar precos.
- Identificar sessoes.
- Salvar historico.

Arquivos principais:
- `src/market_reader.py`
- `src/candle_reader.py`
- `src/price_logger.py`
- `src/candle_logger.py`
- `src/session_engine.py`

## 2. Operador Estrutural

Nome: Market Structure

Missao:
- Detectar BOS.
- Detectar CHOCH.
- Detectar tendencia.
- Detectar mudancas de estrutura.

Arquivos principais:
- `src/bos_engine.py`
- `src/choch_engine.py`
- `src/choch_engine_v2.py`
- `src/trend_reader.py`
- `src/market_structure.py`
- `src/analysis/direction_engine.py`

## 3. Operador de Setup

Nome: Setup Hunter

Missao:
- Validar entradas.
- Conferir momentum.
- Conferir liquidez.
- Conferir contexto.
- Dar nota para o setup.
- Combinar SMC + Elliott como leitura proprietaria do LEON.

Arquivos principais:
- `src/setup_validator.py`
- `src/momentum_reader.py`
- `src/liquidity_engine_v2.py`
- `src/analysis/liquidity_engine.py`
- `src/analysis/setup_score.py`
- `src/smc_engine.py`
- `src/elliott_engine.py`

Saida esperada:
- `SETUP A+`
- `CONFIANCA: 87%`
- `COMPRA` ou `VENDA`

## 4. Operador de Risco

Nome: Risk Manager

Missao:
- Calcular lote.
- Definir Stop Loss.
- Definir Take Profit.
- Controlar drawdown.
- Respeitar limite diario.
- Proteger todos os outros operadores.

Arquivos principais:
- `src/risk_manager.py`
- `src/capital_protection.py`
- `src/execution_guard.py`

## 5. Operador Professor LEON

Nome: Learning Engine

Missao:
- Aprender continuamente.
- Estudar operacoes.
- Avaliar erros.
- Avaliar acertos.
- Melhorar estatisticas.
- Gerar fechamento diario.
- Enviar relatorio diario pelo Telegram.

Arquivos principais:
- `src/learning_engine.py`
- `src/trade_memory.py`
- `src/market_memory.py`
- `src/weekly_review_engine.py`
- `src/journal_engine.py`
- `src/daily_learning_report.py`
- `src/leon_operator.py`

## Hierarquia

```text
PROFESSOR LEON
        ^
        |
SETUP HUNTER
        ^
        |
MARKET STRUCTURE
        ^
        |
MARKET COLLECTOR

RISK MANAGER
(protegendo todos)
```

## Regras de Integridade

- O Telegram comunica resultados; nao decide trades.
- O Professor LEON aprende com memoria; nao substitui a logica principal.
- O Setup Hunter pode usar SMC + Elliott; essa combinacao faz parte da identidade do LEON.
- O Risk Manager protege todos os operadores.
- Alteracoes em BOS, CHOCH, tendencia, setup ou risco exigem aprovacao explicita.
- A autonomia do LEON deve ter prazo definido e pode ser revogada a qualquer momento.

## Autonomia Temporaria

O LEON pode receber autonomia por um periodo determinado.

Escopo atual:
- `learning_only`

Esse escopo permite o funcionamento automatico do Professor LEON para aprendizado, relatorios e comunicacao.

Comandos:

```powershell
python -B src\leon_operator.py --grant-autonomy-minutes 120
python -B src\leon_operator.py --autonomy-status
python -B src\leon_operator.py --revoke-autonomy
```

Limite configurado:
- `config.ini`
- Secao `[AUTONOMY]`
- Campo `max_minutes`

## Proximo Passo

Conectar cada operador a um ciclo coordenado:
- Coleta periodica.
- Analise estrutural.
- Validacao de setup.
- Checagem de risco.
- Registro de aprendizado.
- Comunicacao Telegram.

## Painel de Controle

O painel local do LEON apresenta o status dos operadores:
- Market Collector
- Market Structure
- Setup Hunter
- Alinhamento
- Risk Manager
- Professor LEON
- Telegram

O card de Alinhamento compara:
- Tendencia
- Momentum
- SMC
- Direcao do plano
- Elliott

Estados possiveis:
- `ALINHADO`
- `ATENCAO`
- `CONFLITO`
- `SEM DADOS`

Endereco local:

```text
http://127.0.0.1:8765/
```

Rota tecnica:

```text
http://127.0.0.1:8765/api/operators
```

Envio Telegram do status:

```text
POST http://127.0.0.1:8765/api/operators/send
```

## Heartbeat Telegram

O Professor LEON pode enviar periodicamente o status dos operadores pelo Telegram enquanto a autonomia estiver ativa.

Configuracao:

```ini
[OPERATOR]
telegram_status_enabled=true
telegram_status_interval_minutes=60
```

Comando manual:

```powershell
python -B src\leon_operator.py --send-status
```

Comando manual ignorando intervalo:

```powershell
python -B src\leon_operator.py --send-status --force
```

Arquivo de controle:

```text
data/telegram_status_state.txt
```

## Alerta De Conflito

Quando o alinhamento ficar em `CONFLITO`, o Professor LEON pode enviar um alerta especifico pelo Telegram.

Esse alerta compara:
- Tendencia
- Momentum
- SMC
- Elliott
- Direcao do plano

Comando manual:

```powershell
python -B src\leon_operator.py --send-conflict-alert
```

Comando manual ignorando trava:

```powershell
python -B src\leon_operator.py --send-conflict-alert --force
```

Arquivo de controle:

```text
data/alignment_conflict_state.txt
```

## Alerta De Coleta Antiga

O Market Collector muda para `DADOS ANTIGOS` quando existe historico, mas o ultimo preco/candle nao esta recente.

Esse alerta nao muda a analise do LEON. Ele apenas avisa que a leitura pode estar desatualizada.

Comando manual:

```powershell
python -B src\leon_operator.py --send-stale-data-alert
```

Comando manual ignorando trava:

```powershell
python -B src\leon_operator.py --send-stale-data-alert --force
```

Arquivo de controle:

```text
data/stale_data_state.txt
```

## Coleta Manual

Quando o Market Collector indicar `DADOS ANTIGOS`, o LEON pode tentar atualizar preco e candle manualmente.

Essa acao:
- Le MT5.
- Registra preco.
- Registra candle H1.
- Nao altera BOS.
- Nao altera CHOCH.
- Nao altera Setup Validator.
- Nao executa trade.

Comando:

```powershell
python -B src\leon_operator.py --collect-now
```

Rota do painel:

```text
POST http://127.0.0.1:8765/api/collector/run
```

## Coleta Automatica

O Professor LEON pode manter o Market Collector atualizado enquanto a autonomia estiver ativa.

Configuracao:

```ini
[OPERATOR]
collector_enabled=true
collector_interval_minutes=15
```

O operador continuo deve estar rodando:

```powershell
python -B src\leon_operator.py
```

Quando ativo, ele executa a coleta programada e registra:

```text
OPERATOR | coleta programada executada
```

## Cerebro Contextual

O Professor LEON registra uma memoria contextual em:

```text
data/brain_context_memory.csv
```

Essa memoria guarda:
- Origem do registro.
- Tipo do registro.
- Status do coletor.
- Preco.
- Tendencia.
- Momentum.
- SMC.
- Elliott.
- Direcao.
- Confianca.
- Alinhamento.
- Observacao humana ou automatica.

Ela nao substitui `brain_memory.csv`; ela amplia a capacidade do LEON de estudar contexto.

## Estudo Colaborativo

O painel possui uma entrada para observacoes humanas.

Escopo:
- `study_only`

Configuracao:

```ini
[COLLABORATION]
enabled=true
access_key=<CONFIGURE_LOCALMENTE>
scope=study_only
```

Rota tecnica:

```text
POST http://127.0.0.1:8765/api/study/observation
```

Essa rota salva observacoes no cerebro contextual e nao executa trades.
## Calendario operacional do XAUUSD

O operador acompanha a sessao real informada pela corretora no MetaTrader 5.
Ele nao usa uma tabela fixa de horarios.

- Tick recente e negociacao liberada: coleta, analise e execucao demo ativas.
- Pausa diaria da corretora: operacao suspensa e heartbeat `PAUSA_MERCADO`.
- Fim de semana ou feriado: operacao permanece bloqueada ate novos ticks.
- Apos dois minutos de pausa: a conexao do motor MT5 e reiniciada uma vez.
- Na reabertura: o MT5 e reconectado e coleta, analise e avaliacao demo
  executam imediatamente.

O reinicio e somente do motor operacional LEON/MT5. O Windows e o painel web
nao sao reiniciados. A autonomia temporaria e todas as protecoes de risco
continuam obrigatorias.
