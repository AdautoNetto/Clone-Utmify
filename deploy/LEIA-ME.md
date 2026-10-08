# Log Pose na sua VPS — passo a passo

Tudo aqui foi pensado para **nunca perder venda nem métrica**:

| O quê | Onde fica | Some numa atualização? |
| --- | --- | --- |
| Banco de dados (vendas, clientes, métricas) | volume Docker `logpose_pgdata` | **Não.** Só o programa é trocado; o volume continua. |
| Backups diários | pasta `/opt/logpose/backups` do servidor | **Não.** |
| Programa (app) | container `app` | É recriado a cada atualização (de propósito, não guarda nada). |

- **Backup automático:** um backup ao ligar (ou seja, antes de cada atualização ficar no ar) e outro todo dia às 3h (horário de Brasília). Guarda 14 dias. O arquivo é testado depois de gerado.
- **Cada venda recebida é gravada “crua” antes de ser processada.** Se algo falhar, ela fica guardada e dá para reprocessar (ver “Se uma venda falhar” no fim).
- **Saúde:** `https://SEU-DOMINIO/api/health` responde `{"status":"ok","database":"ok"}` quando está tudo no ar.

> Regra de ouro: **nunca** apague o volume `logpose_pgdata`. No Coolify, ao excluir um recurso, deixe **desmarcada** a opção de apagar volumes. No Docker puro, nunca use `docker compose down -v`.

---

## Antes de começar (só você pode fazer)

1. **Comprar a VPS** — Ubuntu 24.04, mínimo **2 GB de RAM** e 2 vCPU (o Coolify pede isso). ~10 min.
2. **Apontar um subdomínio** para o IP da VPS (ex.: `logpose.seudominio.com.br`, registro tipo **A**). ~5 min, e até 1 h para valer.
3. **Ter este código num repositório seu no GitHub** (as correções feitas aqui estão só no computador; precisam ir para um repositório seu). ~5 min.

## Opção A — Coolify (recomendado: painel visual, HTTPS e atualização automática a cada `git push`)

1. Entre na VPS pelo terminal: `ssh root@IP-DA-VPS` (a senha vem no e-mail da VPS). ~1 min.
2. Instale o Coolify colando: `curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash`. ~5 min.
3. No navegador, abra `http://IP-DA-VPS:8000` e crie a sua conta de administrador do Coolify. ~2 min.
4. Ainda no terminal da VPS, gere duas senhas (rode **duas vezes** e guarde cada resultado no seu gerenciador de senhas): `openssl rand -hex 32`. ~1 min.
5. No Coolify: **Projects → + Add → Production → + New Resource → Private Repository (with GitHub App)** e conecte o seu repositório. ~5 min.
6. Em **Build Pack**, escolha **Docker Compose**. Em **Docker Compose Location**, escreva `/docker-compose.vps.yml`. Clique em **Continue**. ~1 min.
7. Na aba **Environment Variables**, cole você mesmo:
   - `DB_PASSWORD` = a primeira senha do passo 4
   - `SECRET_KEY` = a segunda senha do passo 4
   ~2 min.
8. Na aba **General**, em **Domains for app**, escreva `https://logpose.seudominio.com.br:8000` (o `:8000` diz ao Coolify a porta do app; o endereço público fica sem porta). ~1 min.
9. Clique em **Deploy**. A primeira montagem leva ~5–8 min.
10. Abra `https://logpose.seudominio.com.br/api/health` → tem que aparecer `"database":"ok"`. Depois abra `https://logpose.seudominio.com.br` e crie o usuário dono. ~2 min.

**Atualizar:** dê `git push` no repositório. O Coolify monta a versão nova e troca o app; o banco e os backups ficam.

## Opção B — Docker puro (sem painel)

1. `ssh root@IP-DA-VPS`
2. `git clone <URL-DO-SEU-REPOSITORIO> /opt/logpose/app && cd /opt/logpose/app`
3. `sh deploy/instalar.sh logpose.seudominio.com.br` (instala o Docker se faltar, gera as senhas no servidor, liga tudo com HTTPS). ~8 min.
4. **Atualizar depois:** `cd /opt/logpose/app && sh deploy/atualizar.sh` (faz backup, baixa, troca, confere).

## Backups

- Ver os backups: `ls -lh /opt/logpose/backups`
- Data do último bom: `cat /opt/logpose/backups/ULTIMO-BACKUP-OK`
- Fazer um agora (Docker puro): `docker compose -f docker-compose.vps.yml exec backup backup.sh once`
  (Coolify: aba do recurso → container **backup** → **Execute Command** → `backup.sh once`)
- Restaurar (Docker puro): `sh deploy/backup/restaurar.sh /opt/logpose/backups/<arquivo>.dump` — pede confirmação e faz um backup do estado atual antes.
- **Recomendado:** copiar os backups para fora da VPS de vez em quando (se a VPS inteira sumir, os backups somem junto). Do seu computador: `scp root@IP-DA-VPS:/opt/logpose/backups/*.dump .`

## Se uma venda falhar

As plataformas (Kiwify, PayT) reenviam sozinhas quando recebem erro. Para ver e reprocessar o que falhou (logado como dono/admin):

- `GET /api/webhook-events?status=failed` — lista as falhas, com o motivo.
- `POST /api/webhook-events/<id>/reprocess` — processa de novo a venda guardada.

## Ajustes opcionais (variáveis de ambiente)

| Variável | Padrão | Para quê |
| --- | --- | --- |
| `BACKUP_HOUR` | `03` | hora do backup diário (00–23, Brasília) |
| `BACKUP_KEEP_DAYS` | `14` | quantos dias de backup guardar |
| `BACKUP_DIR` | `/opt/logpose/backups` | pasta dos backups no servidor |
