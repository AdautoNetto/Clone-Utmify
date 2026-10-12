#!/bin/sh
# Publica uma versão nova num servidor PEQUENO (ex.: Oracle Always Free micro).
# Rode no SEU computador (Git Bash), na pasta do projeto, depois do git push:
#
#   SERVIDOR=ubuntu@IP-DO-SERVIDOR sh deploy/publicar-oracle.sh
#
# O que faz: monta o painel aqui (o servidor de 1 GB não aguenta montar),
# envia para /opt/logpose/app/frontend_dist e roda deploy/atualizar.sh lá
# (backup -> git pull -> troca os containers). Banco e backups não são tocados.
set -eu

: "${SERVIDOR:?defina SERVIDOR=usuario@ip (ex.: ubuntu@1.2.3.4)}"
CHAVE="${CHAVE:-$HOME/.ssh/oracle_valetec}"
PASTA="${PASTA:-/opt/logpose/app}"
# Função (e não variável) para o caminho da chave poder ter espaço (ex.: "C:/Users/Nome Sobrenome")
remoto() { ssh -i "$CHAVE" -o BatchMode=yes -o ServerAliveInterval=30 "$SERVIDOR" "$@"; }

echo "== 1/3 Montando o painel"
(cd frontend && npm run build >/dev/null)
[ -f frontend/dist/index.html ] || { echo "Build do painel falhou"; exit 1; }

echo "== 2/3 Enviando o painel"
TMP=$(mktemp -d)
tar --force-local -czf "$TMP/painel.tgz" -C frontend/dist .
scp -q -i "$CHAVE" -o BatchMode=yes "$TMP/painel.tgz" "$SERVIDOR:/tmp/painel.tgz"
rm -rf "$TMP"
remoto "set -e; cd $PASTA; rm -rf frontend_dist.novo; mkdir frontend_dist.novo; tar xzf /tmp/painel.tgz -C frontend_dist.novo; rm -rf frontend_dist; mv frontend_dist.novo frontend_dist; rm -f /tmp/painel.tgz"

echo "== 3/3 Atualizando o servidor (backup, git pull, troca dos containers)"
remoto "cd $PASTA && sudo sh deploy/atualizar.sh"
