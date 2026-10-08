#!/bin/sh
# Backup automático do banco do Log Pose.
#
#   backup.sh loop   (padrão do container) faz um backup ao ligar — ou seja,
#                    antes de cada atualização ficar no ar — e depois um por dia
#                    às BACKUP_HOUR horas (horário de Brasília).
#   backup.sh once   faz um backup agora e sai (usado por "backup manual").
#
# Arquivos: /backups/logpose-AAAA-MM-DD_HHMM.dump (formato do pg_restore,
# já comprimido). Guarda BACKUP_KEEP_DAYS dias. Só apaga antigos DEPOIS de um
# backup novo dar certo, então nunca fica sem nenhum.
set -u

BACKUP_DIR="${BACKUP_PATH:-/backups}"  # dentro do container; a pasta do servidor é montada aqui
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
HOUR="${BACKUP_HOUR:-03}"
STAMP_FILE="$BACKUP_DIR/ULTIMO-BACKUP-OK"
DAY_FILE="$BACKUP_DIR/.ultimo-dia-agendado"

log() { echo "[backup $(date '+%Y-%m-%d %H:%M:%S')] $*"; }

run_backup() {
  mkdir -p "$BACKUP_DIR"
  name="logpose-$(date +%Y-%m-%d_%H%M).dump"
  tmp="$BACKUP_DIR/.$name.parcial"

  log "iniciando $name"
  if ! pg_dump --format=custom --compress=6 --no-owner --file="$tmp"; then
    log "ERRO: pg_dump falhou"
    rm -f "$tmp"
    return 1
  fi
  # Confere se o arquivo abre (backup corrompido é pior que nenhum)
  if ! pg_restore --list "$tmp" >/dev/null 2>&1; then
    log "ERRO: arquivo gerado não abre no pg_restore"
    rm -f "$tmp"
    return 1
  fi
  mv "$tmp" "$BACKUP_DIR/$name"
  echo "$(date '+%Y-%m-%d %H:%M:%S') $name" > "$STAMP_FILE"
  log "ok: $name ($(du -h "$BACKUP_DIR/$name" | cut -f1))"

  find "$BACKUP_DIR" -maxdepth 1 -name 'logpose-*.dump' -mtime +"$KEEP_DAYS" -print -delete \
    | while read -r old; do log "apagado (mais de $KEEP_DAYS dias): $old"; done
  return 0
}

case "${1:-loop}" in
  once)
    run_backup
    exit $?
    ;;
  loop)
    log "agendado: todo dia às ${HOUR}h, guardando ${KEEP_DAYS} dias"
    run_backup || log "backup inicial falhou; tento de novo no horário agendado"
    while true; do
      today=$(date +%F)
      if [ "$(date +%H)" = "$HOUR" ] && [ "$(cat "$DAY_FILE" 2>/dev/null)" != "$today" ]; then
        if run_backup; then
          echo "$today" > "$DAY_FILE"
        else
          sleep 600  # falhou: tenta de novo em 10 min (ainda dentro da mesma hora)
          continue
        fi
      fi
      sleep 60
    done
    ;;
  *)
    echo "uso: backup.sh [loop|once]"
    exit 2
    ;;
esac
