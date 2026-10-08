#!/bin/sh
# Restaura um backup no banco do Log Pose. Rode NO SERVIDOR, na pasta do projeto:
#
#   sh deploy/backup/restaurar.sh /opt/logpose/backups/logpose-2026-10-08_0300.dump
#
# Antes de restaurar, faz um backup do estado atual (para poder desfazer).
# Pede confirmação: SUBSTITUI os dados atuais pelos do arquivo.
set -eu

COMPOSE="docker compose -f docker-compose.vps.yml"
ARQ="${1:-}"

if [ -z "$ARQ" ] || [ ! -f "$ARQ" ]; then
  echo "Uso: sh deploy/backup/restaurar.sh <arquivo .dump>"
  echo "Backups disponíveis:"
  ls -1t "${BACKUP_DIR:-/opt/logpose/backups}"/logpose-*.dump 2>/dev/null | head -20
  exit 1
fi

echo "Isto vai SUBSTITUIR os dados atuais do Log Pose pelos de:"
echo "  $ARQ"
printf "Digite RESTAURAR para continuar: "
read -r resp
[ "$resp" = "RESTAURAR" ] || { echo "Cancelado."; exit 1; }

echo "1/4 Backup de segurança do estado atual..."
$COMPOSE exec -T backup backup.sh once

echo "2/4 Parando o app (para não chegar venda no meio da restauração)..."
$COMPOSE stop app

echo "3/4 Restaurando..."
$COMPOSE exec -T db sh -c 'pg_restore --clean --if-exists --no-owner -U logpose -d logpose' < "$ARQ"

echo "4/4 Ligando o app..."
$COMPOSE start app
echo "Pronto. Vendas avisadas com o app parado: Kiwify/PayT reenviam sozinhas; confira na Plataforma as que não reenviam."
