#!/bin/sh
# Atualiza o Log Pose (Docker puro) com o que está no GitHub, sem perder dados.
# Rode como root na pasta do projeto:  sh deploy/atualizar.sh
#
# O banco fica no volume "logpose_pgdata" e os backups em /opt/logpose/backups:
# recriar os containers não mexe em nenhum dos dois.
set -eu

COMPOSE="docker compose -f docker-compose.vps.yml -f docker-compose.caddy.yml"

echo "== 1/4 Backup antes de atualizar"
$COMPOSE exec -T backup backup.sh once

echo "== 2/4 Baixando a versão nova"
git pull --ff-only

echo "== 3/4 Montando e trocando os containers"
$COMPOSE up -d --build

echo "== 4/4 Conferindo"
sleep 15
$COMPOSE ps
docker compose -f docker-compose.vps.yml exec -T app python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).read().decode())"
