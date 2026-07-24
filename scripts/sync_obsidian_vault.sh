#!/bin/bash
# sync_obsidian_vault.sh
# Sincroniza o vault Obsidian com o sistema de aprendizado diário do LEON
# 
# Uso:
#   ./sync_obsidian_vault.sh          # sincroniza aprendizado diário (bidirecional)
#   ./sync_obsidian_vault.sh status   # mostra status dos arquivos
#   ./sync_obsidian_vault.sh help     # mostra ajuda
#
# Diretórios:
#   OBSIDIAN_VAULT: /opt/leon/app/obsidian_vault/aprendizados_diarios/
#   TAREFAS_LEON:   /opt/leon/app/tarefas/aprendizados_diarios/

OBSIDIAN_DIR="/opt/leon/app/obsidian_vault/aprendizados_diarios"
TAREFAS_DIR="/opt/leon/app/tarefas/aprendizados_diarios"

show_help() {
    echo "sync_obsidian_vault.sh — Sincroniza vault Obsidian com aprendizado diário"
    echo ""
    echo "Uso:"
    echo "  ./sync_obsidian_vault.sh              sincroniza aprendizado diário"
    echo "  ./sync_obsidian_vault.sh status       mostra status dos arquivos"
    echo "  ./sync_obsidian_vault.sh help         mostra esta ajuda"
    echo ""
    echo "Diretórios:"
    echo "  Obsidian: $OBSIDIAN_DIR"
    echo "  Tarefas:  $TAREFAS_DIR"
}

show_status() {
    echo "=== Status dos diretórios de aprendizado diário ==="
    echo ""
    echo "--- Vault Obsidian: $OBSIDIAN_DIR ---"
    ls -la "$OBSIDIAN_DIR" 2>/dev/null || echo "(vazio)"
    echo ""
    echo "--- Tarefas LEON: $TAREFAS_DIR ---"
    ls -la "$TAREFAS_DIR" 2>/dev/null || echo "(vazio)"
    echo ""
    echo "--- Arquivos que existem em ambos ---"
    for f in "$OBSIDIAN_DIR"/*.md "$OBSIDIAN_DIR"/*.txt; do
        bname=$(basename "$f")
        if [ -f "$TAREFAS_DIR/$bname" ]; then
            echo "  SÍNCRONO: $bname"
        elif [ -f "$f" ]; then
            echo "  APENAS OBSIDIAN: $bname"
        fi
    done
    for f in "$TAREFAS_DIR"/*.md "$TAREFAS_DIR"/*.txt; do
        bname=$(basename "$f")
        if [ ! -f "$OBSIDIAN_DIR/$bname" ]; then
            echo "  APENAS TAREFAS: $bname"
        fi
    done
}

sync_daily_learning() {
    echo "=== Sincronizando aprendizado diário ==="
    echo "OBSIDIAN: $OBSIDIAN_DIR"
    echo "TAREFAS:  $TAREFAS_DIR"
    echo ""

    # Sincroniza CONTEXTO_EVOLUCAO.md (bidirecional)
    if [ -f "$OBSIDIAN_DIR/CONTEXTO_EVOLUCAO.md" ] && [ -f "$TAREFAS_DIR/CONTEXTO_EVOLUCAO.md" ]; then
        # Mantém o mais recente
        if [ "$OBSIDIAN_DIR/CONTEXTO_EVOLUCAO.md" -nt "$TAREFAS_DIR/CONTEXTO_EVOLUCAO.md" ]; then
            cp "$OBSIDIAN_DIR/CONTEXTO_EVOLUCAO.md" "$TAREFAS_DIR/CONTEXTO_EVOLUCAO.md"
            echo "  CONTEXTO_EVOLUCAO.md: OBSIDIAN -> TAREFAS"
        elif [ "$TAREFAS_DIR/CONTEXTO_EVOLUCAO.md" -nt "$OBSIDIAN_DIR/CONTEXTO_EVOLUCAO.md" ]; then
            cp "$TAREFAS_DIR/CONTEXTO_EVOLUCAO.md" "$OBSIDIAN_DIR/CONTEXTO_EVOLUCAO.md"
            echo "  CONTEXTO_EVOLUCAO.md: TAREFAS -> OBSIDIAN"
        else
            echo "  CONTEXTO_EVOLUCAO.md: já sincronizado"
        fi
    elif [ -f "$OBSIDIAN_DIR/CONTEXTO_EVOLUCAO.md" ]; then
        cp "$OBSIDIAN_DIR/CONTEXTO_EVOLUCAO.md" "$TAREFAS_DIR/CONTEXTO_EVOLUCAO.md"
        echo "  CONTEXTO_EVOLUCAO.md: OBSIDIAN -> TAREFAS (criado)"
    elif [ -f "$TAREFAS_DIR/CONTEXTO_EVOLUCAO.md" ]; then
        cp "$TAREFAS_DIR/CONTEXTO_EVOLUCAO.md" "$OBSIDIAN_DIR/CONTEXTO_EVOLUCAO.md"
        echo "  CONTEXTO_EVOLUCAO.md: TAREFAS -> OBSIDIAN (criado)"
    fi

    # Sincroniza INDICE.md (bidirecional)
    if [ -f "$OBSIDIAN_DIR/INDICE.md" ] && [ -f "$TAREFAS_DIR/INDICE.md" ]; then
        if [ "$OBSIDIAN_DIR/INDICE.md" -nt "$TAREFAS_DIR/INDICE.md" ]; then
            cp "$OBSIDIAN_DIR/INDICE.md" "$TAREFAS_DIR/INDICE.md"
            echo "  INDICE.md: OBSIDIAN -> TAREFAS"
        elif [ "$TAREFAS_DIR/INDICE.md" -nt "$OBSIDIAN_DIR/INDICE.md" ]; then
            cp "$TAREFAS_DIR/INDICE.md" "$OBSIDIAN_DIR/INDICE.md"
            echo "  INDICE.md: TAREFAS -> OBSIDIAN"
        else
            echo "  INDICE.md: já sincronizado"
        fi
    elif [ -f "$OBSIDIAN_DIR/INDICE.md" ]; then
        cp "$OBSIDIAN_DIR/INDICE.md" "$TAREFAS_DIR/INDICE.md"
        echo "  INDICE.md: OBSIDIAN -> TAREFAS (criado)"
    elif [ -f "$TAREFAS_DIR/INDICE.md" ]; then
        cp "$TAREFAS_DIR/INDICE.md" "$OBSIDIAN_DIR/INDICE.md"
        echo "  INDICE.md: TAREFAS -> OBSIDIAN (criado)"
    fi

    # Sincroniza arquivos de data (YYYY-MM-DD.md)
    for f in "$OBSIDIAN_DIR"/*.md; do
        bname=$(basename "$f")
        if [ "$bname" = "CONTEXTO_EVOLUCAO.md" ] || [ "$bname" = "INDICE.md" ]; then
            continue
        fi
        target="$TAREFAS_DIR/$bname"
        if [ -f "$target" ]; then
            if [ "$f" -nt "$target" ]; then
                cp "$f" "$target"
                echo "  $bname: OBSIDIAN -> TAREFAS"
            elif [ "$target" -nt "$f" ]; then
                cp "$target" "$f"
                echo "  $bname: TAREFAS -> OBSIDIAN"
            fi
        else
            cp "$f" "$target"
            echo "  $bname: OBSIDIAN -> TAREFAS (criado)"
        fi
    done

    # Sincroniza arquivos de data que existem em TAREFAS mas não em OBSIDIAN
    for f in "$TAREFAS_DIR"/*.md; do
        bname=$(basename "$f")
        if [ "$bname" = "CONTEXTO_EVOLUCAO.md" ] || [ "$bname" = "INDICE.md" ]; then
            continue
        fi
        if [ ! -f "$OBSIDIAN_DIR/$bname" ]; then
            cp "$f" "$OBSIDIAN_DIR/$bname"
            echo "  $bname: TAREFAS -> OBSIDIAN (criado)"
        fi
    done

    echo ""
    echo "Sincronização concluída."
}

case "${1:-sync}" in
    sync)
        sync_daily_learning
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Comando desconhecido: $1"
        show_help
        exit 1
        ;;
esac
