"""
Multi-conta: cada pessoa que se cadastra tem os próprios dados e NUNCA enxerga
nem altera os de outra conta.
"""
import re

import bcrypt
import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

import app as app_module
from api.auth import login as entrada
from api.auth import setup as cadastro
from api.auth.ratelimit import SlidingWindow
from api.auth.token import create_access_token
from apoio import SENHA, client, criar_conta, entrar, reset_db, sessao, venda
from database.core.bootstrap import _tenant_tables, bootstrap_database
from database.core.connection import Base, SessionLocal, engine
from database.core.tenancy import account_context
from database.models.customer import Customer
from database.models.transaction import Transaction
from integrations.meta_ads.cache import build_cache_key


@pytest.fixture()
def contas():
    reset_db()
    return criar_conta("ana@teste.com", "Ana"), criar_conta("bruno@teste.com", "Bruno")


def _vendas(conta):
    r = client.get("/api/sales/transactions", headers=conta["auth"])
    assert r.status_code == 200, r.text
    return r.json()


# ── Cadastro ───────────────────────────────────────────────────────────────

def test_cadastro_aberto_cria_conta_e_entra(contas):
    ana, bruno = contas
    assert ana["account_id"] != bruno["account_id"]
    r = client.get("/api/profile", headers=bruno["auth"])
    assert r.status_code == 200 and r.json()["role"] == "owner"
    assert client.get("/api/setup/status").json()["is_configured"] is True


def test_email_nao_repete_nem_com_maiusculas(contas):
    r = client.post("/api/setup", json={
        "name": "Outra", "email": "ANA@teste.com", "password": SENHA, "confirm_password": SENHA})
    assert r.status_code == 400
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM public.accounts")).scalar_one() == 2


def test_senha_curta_e_recusada_e_nao_sobra_conta_pela_metade(contas):
    r = client.post("/api/setup", json={
        "name": "Curta", "email": "curta@teste.com", "password": "1234567", "confirm_password": "1234567"})
    assert r.status_code == 400
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM public.accounts")).scalar_one() == 2
        assert conn.execute(text(
            "SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'conta\\_%'")).scalar_one() == 2


def test_conta_nova_nunca_herda_compartimento_que_ja_existia(contas):
    """Sobra de uma restauração de backup: existe 'conta_3' com dados, mas a conta 3 não existe."""
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE SCHEMA conta_3")
        conn.exec_driver_sql("CREATE TABLE conta_3.transactions (id int, segredo text)")
        conn.exec_driver_sql("INSERT INTO conta_3.transactions VALUES (1, 'dado de outra pessoa')")
    corpo = {"name": "Carla", "email": "carla@teste.com", "password": SENHA, "confirm_password": SENHA}
    assert client.post("/api/setup", json=corpo).status_code == 503
    assert client.post("/api/login", json={"email": "carla@teste.com", "password": SENHA}).status_code == 401
    assert client.post("/api/setup", json=corpo).status_code == 200  # tentar de novo funciona
    carla = entrar("carla@teste.com")
    r = client.get("/api/sales/transactions", headers=carla)
    assert r.status_code == 200 and r.json()["total"] == 0
    with engine.connect() as conn:
        assert conn.execute(text("SELECT segredo FROM conta_3.transactions")).scalar_one() == "dado de outra pessoa"
        assert conn.execute(text(
            "SELECT account_id FROM public.admins WHERE email = 'carla@teste.com'")).scalar_one() == 4


def test_limite_de_cadastros_por_conexao(contas, monkeypatch):
    monkeypatch.setattr(cadastro, "signup_limiter", SlidingWindow(2, 3600))
    codigos = []
    for i in range(3):
        r = client.post("/api/setup", json={
            "name": f"R{i}", "email": f"robo{i}@teste.com", "password": SENHA, "confirm_password": SENHA})
        codigos.append(r.status_code)
    assert codigos == [200, 200, 429]


def test_login_trava_depois_de_muitas_senhas_erradas(contas, monkeypatch):
    monkeypatch.setattr(entrada, "login_failures", SlidingWindow(3, 900))
    for _ in range(3):
        r = client.post("/api/login", json={"email": "ana@teste.com", "password": "errada-errada"})
        assert r.status_code == 401
    r = client.post("/api/login", json={"email": "ana@teste.com", "password": SENHA})
    assert r.status_code == 429
    # outra pessoa (outro e-mail) continua entrando
    assert client.post("/api/login", json={"email": "bruno@teste.com", "password": SENHA}).status_code == 200


# ── Vendas: cada uma na sua conta ──────────────────────────────────────────

def test_venda_de_uma_conta_nao_aparece_na_outra(contas):
    ana, bruno = contas
    assert client.post(ana["url"], json=venda("PED-ANA", customer_email="c1@exemplo.com.br")).status_code == 200
    assert _vendas(ana)["total"] == 1
    assert _vendas(bruno)["total"] == 0
    for rota in ("/api/customers", "/api/dashboard/overview", "/api/sales/summary", "/api/webhook-events"):
        r = client.get(rota, headers=bruno["auth"])
        assert r.status_code == 200, f"{rota}: {r.text}"
        assert "PED-ANA" not in r.text and "c1@exemplo.com.br" not in r.text, rota
    assert "c1@exemplo.com.br" in client.get("/api/customers", headers=ana["auth"]).text


def test_mesmo_pedido_e_mesmo_cliente_em_duas_contas_nao_se_misturam(contas):
    ana, bruno = contas
    assert client.post(ana["url"], json=venda("PED-1", amount=100.0)).status_code == 200
    assert client.post(bruno["url"], json=venda("PED-1", amount=40.0)).status_code == 200
    for conta, valor in ((ana, 100.0), (bruno, 40.0)):
        with sessao(conta["account_id"]) as db:
            assert db.query(Transaction).one().amount == valor
            cliente = db.query(Customer).one()
            assert (cliente.total_orders, cliente.total_spent) == (1, valor)


def test_conta_nao_apaga_venda_da_outra(contas):
    ana, bruno = contas
    client.post(ana["url"], json=venda("PED-ANA"))
    tx_id = _vendas(ana)["items"][0]["id"]
    r = client.delete(f"/api/sales/transactions/{tx_id}", headers=bruno["auth"])
    assert r.status_code == 404
    assert _vendas(ana)["total"] == 1


def test_zerar_vendas_de_uma_conta_nao_toca_na_outra(contas):
    ana, bruno = contas
    client.post(ana["url"], json=venda("PED-ANA"))
    client.post(bruno["url"], json=venda("PED-BRUNO"))
    with sessao(bruno["account_id"]) as db:
        db.query(Transaction).delete()
        db.commit()
    assert _vendas(ana)["total"] == 1
    assert _vendas(bruno)["total"] == 0


def test_endereco_de_vendas_e_de_uma_conta_so(contas):
    ana, bruno = contas
    lista_bruno = client.get("/api/platforms/webhooks", headers=bruno["auth"]).json()
    assert [w["slug"] for w in lista_bruno] == [bruno["slug"]]
    # Bruno apaga o endereço DELE; o da Ana continua recebendo
    r = client.delete(f"/api/platforms/webhooks/{bruno['endpoint_id']}", headers=bruno["auth"])
    assert r.status_code == 204
    assert client.post(bruno["url"], json=venda("PED-X")).status_code == 404
    assert client.post(ana["url"], json=venda("PED-ANA")).status_code == 200
    assert _vendas(bruno)["total"] == 0


def test_login_de_outra_conta_no_cabecalho_nao_desvia_a_venda(contas):
    """A conta de uma venda é a dona do endereço, mesmo que venha um login de outra conta junto."""
    ana, bruno = contas
    r = client.post(ana["url"], json=venda("PED-ANA"), headers=bruno["auth"])
    assert r.status_code == 200
    assert _vendas(ana)["total"] == 1 and _vendas(bruno)["total"] == 0


# ── Equipe (convidados) ────────────────────────────────────────────────────

def _convidar(conta, papel, email):
    r = client.post("/api/users/invite", json={"name": papel, "role": papel}, headers=conta["auth"])
    assert r.status_code == 200, r.text
    r2 = client.post(f"/api/setup/invite/{r.json()['invite_token']}", json={
        "email": email, "password": SENHA, "confirm_password": SENHA})
    assert r2.status_code == 200, r2.text
    return r.json()["id"]


def test_convidado_entra_na_conta_de_quem_convidou(contas):
    ana, bruno = contas
    client.post(ana["url"], json=venda("PED-ANA"))
    _convidar(ana, "viewer", "ajudante@teste.com")
    ajudante = entrar("ajudante@teste.com")
    r = client.get("/api/sales/transactions", headers=ajudante)
    assert r.status_code == 200 and r.json()["total"] == 1


def test_equipe_de_uma_conta_nao_aparece_nem_e_alterada_pela_outra(contas):
    ana, bruno = contas
    ajudante_id = _convidar(ana, "admin", "ajudante@teste.com")
    emails_bruno = [u["email"] for u in client.get("/api/users", headers=bruno["auth"]).json()]
    assert emails_bruno == ["bruno@teste.com"]
    for metodo, rota, corpo in (
        ("DELETE", f"/api/users/{ajudante_id}", None),
        ("PUT", f"/api/users/{ajudante_id}/role", {"role": "viewer"}),
        ("PUT", f"/api/users/{ajudante_id}/reset-password", {"new_password": SENHA + "x", "confirm_password": SENHA + "x"}),
    ):
        r = client.request(metodo, rota, json=corpo, headers=bruno["auth"])
        assert r.status_code == 404, f"{metodo} {rota} -> {r.status_code}"
    assert entrar("ajudante@teste.com")  # senha e acesso intactos
    usuarios_ana = client.get("/api/users", headers=ana["auth"]).json()
    assert [(u["email"], u["role"]) for u in usuarios_ana] == [
        ("ana@teste.com", "owner"), ("ajudante@teste.com", "admin")]


# ── Login/token ────────────────────────────────────────────────────────────

def test_token_apontando_para_outra_conta_e_recusado(contas):
    ana, bruno = contas
    client.post(bruno["url"], json=venda("PED-BRUNO"))
    with engine.connect() as conn:
        ana_id = conn.execute(text("SELECT id FROM public.admins WHERE email = 'ana@teste.com'")).scalar_one()
    forjado = create_access_token({"sub": str(ana_id), "acc": bruno["account_id"], "role": "owner"})
    r = client.get("/api/sales/transactions", headers={"Authorization": f"Bearer {forjado}"})
    assert r.status_code == 401
    antigo = create_access_token({"sub": str(ana_id), "role": "owner"})  # login de antes do multi-conta
    r = client.get("/api/sales/transactions", headers={"Authorization": f"Bearer {antigo}"})
    assert r.status_code == 401


_ROTAS_PUBLICAS = {"/api/login", "/api/setup", "/api/setup/status", "/api/setup/invite/{token}",
                   "/api/webhook/{platform}/{slug}"}


def test_sem_login_nenhuma_rota_entrega_dado(contas):
    """Varre o app inteiro: toda rota (atual ou futura) fora das públicas exige login."""
    testadas, vazou = 0, []
    for path, metodos in app_module.app.openapi()["paths"].items():
        if not path.startswith("/api") or path in _ROTAS_PUBLICAS:
            continue
        for method in (m.upper() for m in metodos):
            r = client.request(method, re.sub(r"\{[^}]+\}", "1", path), json={})
            testadas += 1
            if r.status_code not in (401, 403):
                vazou.append(f"{method} {path} -> {r.status_code}")
    assert testadas > 80
    assert vazou == []


# ── A trava no banco ───────────────────────────────────────────────────────

def test_sessao_sem_conta_nao_enxerga_venda_nenhuma(contas):
    """Mesmo logo depois de uma requisição da Ana, uma sessão 'solta' não vê as tabelas dela."""
    ana, _ = contas
    client.post(ana["url"], json=venda("PED-ANA"))
    assert _vendas(ana)["total"] == 1
    for _ in range(8):  # passa por várias conexões do pool
        with SessionLocal() as db:
            with pytest.raises(ProgrammingError):
                db.query(Transaction).count()


def test_tabelas_de_negocio_nao_existem_fora_dos_compartimentos(contas):
    nomes = {t.name for t in _tenant_tables()}
    assert {"transactions", "customers", "products", "facebook_accounts", "webhook_events"} <= nomes
    with engine.connect() as conn:
        no_public = set(conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars())
    assert no_public == {"accounts", "admins", "webhook_routes"}


def test_cache_de_anuncios_e_separado_por_conta(contas):
    ana, bruno = contas
    with account_context(ana["account_id"]):
        chave_ana = build_cache_key("act_1", "insights", "2026-01-01", "2026-01-31")
    with account_context(bruno["account_id"]):
        chave_bruno = build_cache_key("act_1", "insights", "2026-01-01", "2026-01-31")
    assert chave_ana != chave_bruno


# ── Quem já usava a versão de conta única ──────────────────────────────────

def test_instalacao_de_conta_unica_vira_a_conta_1_sem_perder_nada():
    reset_db()
    hash_senha = bcrypt.hashpw(SENHA.encode(), bcrypt.gensalt()).decode()
    with engine.begin() as conn:
        # Monta o banco como a versão antiga deixava: tudo no "public", usuário sem conta
        conn.exec_driver_sql("SET LOCAL search_path TO public")
        Base.metadata.create_all(bind=conn, tables=_tenant_tables())
        conn.exec_driver_sql("ALTER TABLE public.admins DROP COLUMN account_id")
        conn.execute(text(
            "INSERT INTO public.admins (name, email, password_hash, role) "
            "VALUES ('Dona Antiga', 'antiga@teste.com', :h, 'owner')"), {"h": hash_senha})
        conn.exec_driver_sql(
            "INSERT INTO public.webhook_endpoints (slug, platform, name) VALUES ('slugantigo', 'API', 'Loja')")
        conn.exec_driver_sql(
            "INSERT INTO public.customers (email, name, total_spent, total_orders) "
            "VALUES ('velho@exemplo.com.br', 'Cliente Velho', 197, 1)")
        conn.exec_driver_sql(
            "INSERT INTO public.transactions (external_id, platform, status, amount, customer_id, customer_email) "
            "VALUES ('PED-VELHO', 'API', 'APPROVED', 197, 1, 'velho@exemplo.com.br')")

    bootstrap_database()
    bootstrap_database()  # rodar de novo (todo boot) não muda nada

    with engine.connect() as conn:
        no_public = set(conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars())
        assert no_public == {"accounts", "admins", "webhook_routes"}
        assert conn.execute(text("SELECT count(*) FROM public.accounts")).scalar_one() == 1
    dona = entrar("antiga@teste.com")
    lista = client.get("/api/sales/transactions", headers=dona).json()
    assert [t["external_id"] for t in lista["items"]] == ["PED-VELHO"]
    # o endereço de vendas antigo continua valendo
    r = client.post("/api/webhook/api/slugantigo", json=venda("PED-NOVO", customer_email="velho@exemplo.com.br"))
    assert r.status_code == 200, r.text
    with sessao(1) as db:
        assert db.query(Transaction).count() == 2
        assert db.query(Customer).one().total_orders == 2
    # e uma conta nova, criada depois, nasce vazia
    nova = criar_conta("nova@teste.com", "Nova")
    assert _vendas(nova)["total"] == 0
