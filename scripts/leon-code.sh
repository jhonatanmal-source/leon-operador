#!/usr/bin/env bash
# ============================================
# LEON OpenCode Session Manager
# ============================================
# Gerencia sessões OpenCode: ao abrir uma nova
# sessão terminal, fecha automaticamente a
# anterior para evitar acúmulo de recursos.
#
# Preserva o servidor web (opencode web) e a
# interface web (sessão principal).
# ============================================
set -euo pipefail

cd /opt/leon/app

PIDFILE="/tmp/leon-code-terminal.pid"
WEB_MARKER="opencode web"

# ── Fecha sessão terminal anterior ──────────
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE" 2>/dev/null || echo "")
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        # Verifica se é um processo opencode (não web server)
        CMDLINE=$(cat /proc/"$OLD_PID"/cmdline 2>/dev/null | tr '\0' ' ' || echo "")
        if echo "$CMDLINE" | grep -q "bin/opencode" && \
           ! echo "$CMDLINE" | grep -q "$WEB_MARKER"; then
            echo "[leon-code] Fechando sessão anterior (PID $OLD_PID)..."
            kill "$OLD_PID" 2>/dev/null || true
            sleep 0.5
            kill -0 "$OLD_PID" 2>/dev/null && kill -9 "$OLD_PID" 2>/dev/null || true
        fi
    fi
fi

# ── Registra PID desta sessão ───────────────
echo "$$" > "$PIDFILE"

# ── Executa OpenCode ────────────────────────
exec /home/leon/.opencode/bin/opencode "$@"
