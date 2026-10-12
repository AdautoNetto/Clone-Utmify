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

## Várias contas (cada pessoa com a sua)

- Qualquer pessoa abre o endereço, clica em **Criar conta** e se cadastra com nome, e-mail e senha
  (mínimo 8 caracteres). Um e-mail = uma conta.
- **Os dados de cada conta ficam separados dentro do banco** (um compartimento por conta: vendas,
  clientes, produtos, chaves do Facebook/Gemini, endereços de venda). Uma conta não vê nem altera a outra.
- O dono de uma conta pode convidar pessoas (menu **Usuários**): elas entram **na conta dele**, como
  administrador ou só visualização.
- Proteções do cadastro aberto: no máximo 20 contas novas por hora vindas da mesma conexão (`SIGNUP_MAX_PER_HOUR`), 10 senhas
  erradas travam aquele e-mail por 15 minutos, e há um teto de contas (`MAX_ACCOUNTS`, padrão 300).
- Para **fechar o cadastro** (ninguém novo entra; quem já tem conta continua usando): coloque
  `SIGNUP_ENABLED=0` no `.env` do servidor e rode `sudo sh deploy/atualizar.sh`.
- Quem já usava a versão de conta única: na primeira subida da versão nova, tudo o que existia vira a
  **conta nº 1** (do dono antigo), sem perder nada. Todos precisam fazer login de novo uma vez.

### Quem administra o sistema (tela Contas)

- **A primeira conta criada administra o sistema.** Só ela vê o menu **Contas** (no celular: Mais → Contas).
- Em **Contas** aparecem todas as contas (dono, usuários, número de vendas, última venda) e, em **Ações**:
  - **Link de senha nova:** gera um link de uso único (24 h) para o dono daquela conta criar outra senha.
  - **Bloquear / Desbloquear:** ninguém daquela conta entra; as vendas dela continuam sendo recebidas.
  - **Excluir conta:** apaga os logins e todos os dados daquela conta. Pede o e-mail do dono para
    confirmar. Só volta restaurando um backup. Não dá para bloquear nem excluir a própria conta.

### Esqueci minha senha

- Na tela de login há o link **Esqueci minha senha**.
- **Com envio de e-mail ligado:** a pessoa digita o e-mail e recebe um link (vale 1 hora, uma vez só).
- **Sem envio de e-mail:** a tela avisa para pedir o link a quem administra o sistema, que o gera em
  **Contas → Ações → Link de senha nova** e manda por WhatsApp, por exemplo.
- **Ligar o envio de e-mail** (em **Contas → Envio de e-mail**, só quem administra): servidor
  (`smtp.gmail.com`), porta (`465`), o e-mail que envia, a **senha de app** desse e-mail, o nome que
  aparece para quem recebe e o endereço do painel. Salve e use **Enviar e-mail de teste para mim**.
  A senha de app fica guardada no servidor e nunca volta para a tela.

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
10. Abra `https://logpose.seudominio.com.br/api/health` → tem que aparecer `"database":"ok"`. Depois abra `https://logpose.seudominio.com.br` e clique em **Criar conta**. ~2 min.

**Atualizar:** dê `git push` no repositório. O Coolify monta a versão nova e troca o app; o banco e os backups ficam.

## Opção B — Docker puro (sem painel)

1. `ssh root@IP-DA-VPS`
2. `git clone <URL-DO-SEU-REPOSITORIO> /opt/logpose/app && cd /opt/logpose/app`
3. `sh deploy/instalar.sh logpose.seudominio.com.br` (instala o Docker se faltar, gera as senhas no servidor, liga tudo com HTTPS). ~8 min.
4. **Atualizar depois:** `cd /opt/logpose/app && sh deploy/atualizar.sh` (faz backup, baixa, troca, confere).

## Opção C — Oracle Cloud "Always Free" (máquina micro de 1 GB)

Foi o caminho usado na instalação atual. Diferenças para as opções acima:

- A máquina gratuita que costuma ter vaga é a **VM.Standard.E2.1.Micro** (1 GB de memória). A ARM
  (A1.Flex, bem mais forte) vive com "capacidade insuficiente" em São Paulo; vale tentar de novo depois.
- Com 1 GB **não dá para montar o painel dentro do servidor**. O painel é montado no seu computador e
  enviado pronto (pasta `frontend_dist`); os scripts percebem a pasta e usam `Dockerfile.prebuilt`.
- A Oracle tem **dois** bloqueios de porta: a "Lista de Segurança" da sub-rede (no painel da Oracle) e o
  firewall interno do Ubuntu. Os dois precisam liberar 80 e 443.

Passos (uma vez):

1. No painel da Oracle: criar a rede pelo **Assistente de VCN** ("VCN com conectividade de internet") e a
   instância **Ubuntu 24.04 / VM.Standard.E2.1.Micro** na sub-rede pública, com IP público e a sua chave SSH.
2. Na Lista de Segurança padrão da rede: regra de entrada **TCP 80,443** de `0.0.0.0/0`.
3. No servidor: `git clone <repo> /opt/logpose/app && cd /opt/logpose/app && sudo sh deploy/oracle-preparar.sh`
   (cria 3 GB de swap e libera 80/443 no firewall interno).
4. No seu computador: `SERVIDOR=ubuntu@IP sh deploy/publicar-oracle.sh` envia o painel (na 1ª vez, envie o
   painel e depois rode no servidor `sudo sh deploy/instalar.sh <dominio>`).

Sem domínio próprio, use `IP-COM-TRACOS.sslip.io` (ex.: `137-131-175-179.sslip.io`): aponta sozinho para o
IP e o Caddy consegue o cadeado (HTTPS) normalmente. Quando tiver um subdomínio, troque `DOMINIO` no `.env`
do servidor e rode `sudo sh deploy/atualizar.sh`.

**Atualizar depois:** `git push` e, no seu computador, `SERVIDOR=ubuntu@IP sh deploy/publicar-oracle.sh`.

## Vercel na frente (link bonito para o painel)

A Vercel não roda este sistema sozinha (ele precisa de servidor ligado 24h e de banco). O que dá para
fazer é publicar **só o painel** na Vercel e deixar que ela repasse tudo de `/api` para o servidor:

1. No computador, na pasta `frontend`: `VITE_WEBHOOK_ORIGIN=https://ENDERECO-DO-SERVIDOR npx vite build --outDir <pasta>`
   (com essa variável, o endereço de vendas mostrado em **Plataformas** aponta direto para o servidor:
   a venda não passa pela Vercel).
2. Na pasta gerada, um `vercel.json` com dois repasses: `/api/:path*` → `https://ENDERECO-DO-SERVIDOR/api/:path*`
   e o resto → `/index.html`.
3. `vercel deploy --prod` nessa pasta. A cada mudança no painel, repetir os passos 1 e 3.

Os dados continuam no servidor; se o endereço do servidor mudar, refaça os passos 1 a 3.

## Backups

- Ver os backups: `ls -lh /opt/logpose/backups`
- Data do último bom: `cat /opt/logpose/backups/ULTIMO-BACKUP-OK`
- Fazer um agora (Docker puro): `docker compose -f docker-compose.vps.yml exec backup backup.sh once`
  (Coolify: aba do recurso → container **backup** → **Execute Command** → `backup.sh once`)
- Restaurar (Docker puro): `sh deploy/backup/restaurar.sh /opt/logpose/backups/<arquivo>.dump` — pede confirmação e faz um backup do estado atual antes. Restaura **todas as contas** como estavam naquele backup (contas criadas depois dele deixam de existir; estão no backup de segurança feito na hora).
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
| `SIGNUP_ENABLED` | `1` | `0` fecha o cadastro de contas novas |
| `MAX_ACCOUNTS` | `300` | número máximo de contas no sistema |
