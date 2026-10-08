#!/bin/sh
# Instalação do Log Pose numa VPS Ubuntu/Debian SEM Coolify (Docker puro + HTTPS pelo Caddy).
# Rode como root, dentro da pasta do projeto clonado:
#
#   sh deploy/instalar.sh logpose.seudominio.com.br
#
# Gera as senhas NO PRÓPRIO SERVIDOR (ninguém precisa ver nem copiar) e salva em .env.
# Pode rodar de novo sem medo: não troca senhas existentes nem apaga dados.
set -eu

DOMINIO="${1:-}"
[ -n "$DOMINIO" ] || { echo "Uso: sh deploy/instalar.sh <dominio>"; exit 1; }
[ -f docker-compose.vps.yml ] || { echo "Rode dentro da pasta do projeto (onde está docker-compose.vps.yml)"; exit 1; }

if ! command -v docker >/dev/null 2>&1; then
  echo "== Instalando Docker (script oficial get.docker.com)"
  curl -fsSL https://get.docker.com | sh
fi

if [ ! -f .env ]; then
  echo "== Criando .env com senhas aleatórias"
  umask 077
  {
    echo "DB_PASSWORD=$(openssl rand -hex 32)"
    echo "SECRET_KEY=$(openssl rand -hex 32)"
    echo "DOMINIO=$DOMINIO"
    echo "BACKUP_DIR=/opt/logpose/backups"
  } > .env
else
  echo "== .env já existe: mantido (senhas não mudam)"
  grep -q '^DOMINIO=' .env || echo "DOMINIO=$DOMINIO" >> .env
fi
chmod 600 .env
mkdir -p /opt/logpose/backups

echo "== Subindo (primeira vez demora uns 5 minutos para montar)"
docker compose -f docker-compose.vps.yml -f docker-compose.caddy.yml up -d --build

echo "== Esperando o app responder"
i=0
until docker compose -f docker-compose.vps.yml exec -T app python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)" >/dev/null 2>&1; do
  i=$((i + 1))
  [ "$i" -lt 60 ] || { echo "O app não respondeu em 5 min. Veja: docker compose -f docker-compose.vps.yml logs app"; exit 1; }
  sleep 5
done

docker compose -f docker-compose.vps.yml -f docker-compose.caddy.yml ps
echo
echo "OK. Abra https://$DOMINIO e crie o usuário dono."
echo "Backups diários em /opt/logpose/backups (o primeiro já foi feito agora)."
echo "NUNCA rode 'docker compose down -v' (o -v apaga o banco)."
