#!/bin/bash
# Iniciar Bot de Comandos Telegram do LEON
# Uso: ./scripts/iniciar_bot_telegram.sh [start|stop|status|restart]

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SESSION_NAME="leon-telegram"

case "${1:-start}" in
    start)
        if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "✅ Bot já está rodando (sessão: $SESSION_NAME)"
            exit 0
        fi
        cd "$SCRIPT_DIR" && tmux new-session -d -s "$SESSION_NAME" \
            "python3 src/telegram_commands_mcp.py" 2>&1
        sleep 1
        if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "✅ Bot de comandos Telegram iniciado (sessão: $SESSION_NAME)"
        else
            echo "❌ Falha ao iniciar bot"
            exit 1
        fi
        ;;
    stop)
        if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            tmux kill-session -t "$SESSION_NAME"
            echo "🛑 Bot parado"
        else
            echo "ℹ️ Bot não estava rodando"
        fi
        ;;
    status)
        if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "✅ Bot está RODANDO (sessão: $SESSION_NAME)"
            tmux capture-pane -t "$SESSION_NAME" -p -S -5
        else
            echo "❌ Bot está PARADO"
        fi
        ;;
    restart)
        "$0" stop
        sleep 1
        "$0" start
        ;;
    *)
        echo "Uso: $0 [start|stop|status|restart]"
        exit 1
        ;;
esac
