#!/usr/bin/env bash
# ============================================
# LEON Vault Unlock — Decrypt .env for startup
# ============================================
# Called by systemd ExecStartPre to decrypt
# the .env.encrypted vault into .env before
# the LEON service starts.
#
# Usage:
#   ./scripts/unlock_env.sh          # decrypt vault
#   ./scripts/unlock_env.sh --status  # check vault status
# ============================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MASTER_KEY="/opt/leon/.master_key"
ENCRYPTED_ENV="$PROJECT_ROOT/.env.encrypted"
ENV_FILE="$PROJECT_ROOT/.env"

if [ "${1:-}" = "--status" ]; then
    echo "Vault Status:"
    echo "  Master key: $([ -f "$MASTER_KEY" ] && echo 'EXISTS' || echo 'NOT FOUND')"
    echo "  Encrypted:  $([ -f "$ENCRYPTED_ENV" ] && echo 'EXISTS' || echo 'NOT FOUND')"
    echo "  .env file:  $([ -f "$ENV_FILE" ] && echo 'EXISTS' || echo 'NOT FOUND')"
    exit 0
fi

# If .env already exists, no need to decrypt
if [ -f "$ENV_FILE" ] && [ -s "$ENV_FILE" ]; then
    exit 0
fi

# If encrypted vault exists, decrypt it
if [ -f "$ENCRYPTED_ENV" ]; then
    if [ ! -f "$MASTER_KEY" ]; then
        echo "[VAULT] ERROR: Master key not found at $MASTER_KEY" >&2
        exit 1
    fi
    cd "$PROJECT_ROOT" && python3 -m src.vault decrypt
    echo "[VAULT] .env decrypted successfully"
else
    echo "[VAULT] No encrypted vault found. Starting without secret management."
fi
