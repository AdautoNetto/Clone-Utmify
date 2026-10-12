#!/bin/sh
# Publica o PAINEL na Vercel ("Vercel na frente"): link bonito para as pessoas,
# com tudo de /api repassado para o servidor. Rode no SEU computador (Git Bash),
# na pasta do projeto, depois de publicar o servidor:
#
#   SERVIDOR_URL=https://endereco-do-servidor PASTA_VERCEL="/c/Users/Voce/vale-tec-vendas" \
#     VERCEL="vercel" ESCOPO=sua-equipe sh deploy/publicar-vercel.sh
#
# PASTA_VERCEL é a pasta ligada ao projeto da Vercel (tem a subpasta .vercel).
set -eu

: "${SERVIDOR_URL:?defina SERVIDOR_URL=https://endereco-do-servidor}"
: "${PASTA_VERCEL:?defina PASTA_VERCEL=pasta ligada ao projeto da Vercel}"
VERCEL="${VERCEL:-vercel}"
[ -d "$PASTA_VERCEL/.vercel" ] || { echo "A pasta $PASTA_VERCEL não está ligada a um projeto da Vercel (.vercel não existe)"; exit 1; }

TMP=$(mktemp -d)
echo "== 1/3 Montando o painel (o endereço de vendas aponta direto para o servidor)"
(cd frontend && VITE_WEBHOOK_ORIGIN="$SERVIDOR_URL" npx vite build --outDir "$TMP/painel" --emptyOutDir >/dev/null)
[ -f "$TMP/painel/index.html" ] || { echo "Build do painel falhou"; exit 1; }

echo "== 2/3 Copiando para a pasta da Vercel e gerando o vercel.json"
rm -rf "$PASTA_VERCEL/assets"
cp -r "$TMP/painel/." "$PASTA_VERCEL/"
node deploy/vercel-config.js "$PASTA_VERCEL" "$SERVIDOR_URL"
rm -rf "$TMP"

echo "== 3/3 Publicando"
cd "$PASTA_VERCEL"
# shellcheck disable=SC2086
$VERCEL deploy --prod --yes ${ESCOPO:+--scope "$ESCOPO"}
