#!/bin/bash
# backup_operational_data.sh
# Backup dedicado dos dados operacionais do LEON (CSVs e JSON de estado em data/).
#
# Motivacao: o incidente de 2026-08-17 (teste truncou pre_operation_trades.csv)
# so foi irreversivel no workspace porque nao havia backup frequente e dedicado
# dos CSVs operacionais. Os backups full diarios (/opt/leon/backups/leon_*.tar.gz)
# rodam 1x/dia as ~03:00 e sao pesados (~45 MB). Este script faz um snapshot
# leve (~14 MB) SO dos dados operacionais, com rotacao, para permitir recuperacao
# granular e frequente.
#
# Seguranca:
#   - SOMENTE LEITURA sobre data/. Nunca escreve/apaga em data/.
#   - Nao envia ordens, nao toca MT5, nao altera operacional.
#   - Grava snapshots em BACKUP_DIR com rotacao por retencao.
#
# Uso:
#   ./backup_operational_data.sh            # cria snapshot e aplica rotacao
#   ./backup_operational_data.sh status     # lista snapshots existentes
#   ./backup_operational_data.sh verify     # verifica integridade do ultimo snapshot

set -euo pipefail

APP_DIR="/opt/leon/app"
DATA_DIR="${APP_DIR}/data"                       # symlink -> /opt/leon/data
BACKUP_DIR="/opt/leon/backups/operational_data"
RETENTION="${LEON_BACKUP_RETENTION:-48}"         # snapshots mantidos (48 = ~48h se horario)
TS="$(date +%Y%m%d_%H%M%S)"
ARCHIVE="${BACKUP_DIR}/opdata_${TS}.tar.gz"

log() { echo "[backup_operational_data] $*"; }

cmd_backup() {
  mkdir -p "${BACKUP_DIR}"
  if [ ! -d "${DATA_DIR}" ]; then
    log "ERRO: ${DATA_DIR} nao encontrado"; exit 1
  fi

  # Arquiva SOMENTE os arquivos de dados operacionais (csv/json/txt de estado).
  # -h resolve o symlink data/ -> /opt/leon/data.
  tar -czhf "${ARCHIVE}" \
      -C "${APP_DIR}" \
      --exclude='data/backtests' \
      --exclude='data/learning' \
      $(cd "${APP_DIR}" && ls data/*.csv data/*.json data/*.txt 2>/dev/null) \
      2>/dev/null

  # Checksum para verificacao de integridade futura.
  sha256sum "${ARCHIVE}" | awk '{print $1}' > "${ARCHIVE}.sha256"

  local size
  size="$(du -h "${ARCHIVE}" | cut -f1)"
  log "snapshot criado: ${ARCHIVE} (${size})"

  cmd_rotate
}

cmd_rotate() {
  local total
  total="$(ls -1t "${BACKUP_DIR}"/opdata_*.tar.gz 2>/dev/null | wc -l)"
  if [ "${total}" -gt "${RETENTION}" ]; then
    ls -1t "${BACKUP_DIR}"/opdata_*.tar.gz | tail -n +$((RETENTION + 1)) | while read -r old; do
      rm -f "${old}" "${old}.sha256"
      log "rotacionado (removido): $(basename "${old}")"
    done
  fi
}

cmd_status() {
  log "snapshots em ${BACKUP_DIR}:"
  ls -1t "${BACKUP_DIR}"/opdata_*.tar.gz 2>/dev/null | while read -r f; do
    printf "  %s  %s\n" "$(du -h "${f}" | cut -f1)" "$(basename "${f}")"
  done
  local total
  total="$(ls -1t "${BACKUP_DIR}"/opdata_*.tar.gz 2>/dev/null | wc -l)"
  log "total: ${total} (retencao: ${RETENTION})"
}

cmd_verify() {
  local last
  last="$(ls -1t "${BACKUP_DIR}"/opdata_*.tar.gz 2>/dev/null | head -1)"
  if [ -z "${last}" ]; then
    log "nenhum snapshot encontrado"; exit 1
  fi
  if [ ! -f "${last}.sha256" ]; then
    log "sem checksum para ${last}"; exit 1
  fi
  local expected actual
  expected="$(cat "${last}.sha256")"
  actual="$(sha256sum "${last}" | awk '{print $1}')"
  if [ "${expected}" = "${actual}" ]; then
    log "OK: ${last} integro (sha256 confere)"
    tar -tzf "${last}" >/dev/null && log "OK: arquivo tar legivel"
  else
    log "FALHA: checksum divergente em ${last}"; exit 1
  fi
}

case "${1:-backup}" in
  backup) cmd_backup ;;
  status) cmd_status ;;
  verify) cmd_verify ;;
  *) echo "uso: $0 [backup|status|verify]"; exit 2 ;;
esac
