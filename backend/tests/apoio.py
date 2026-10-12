"""Peças comuns dos testes: cliente HTTP, limpeza do banco e criação de contas."""
from fastapi.testclient import TestClient
from sqlalchemy import text

import app as app_module
from api.auth import password_reset
from api.auth.login import login_failures
from api.auth.setup import signup_limiter
from database.core.connection import account_session, engine

client = TestClient(app_module.app)
SENHA = "senha-teste-123"


def reset_db():
    """Apaga TODAS as contas (compartimentos e usuários). Só para banco de teste."""
    with engine.begin() as conn:
        schemas = conn.execute(text(
            "SELECT nspname FROM pg_namespace "
            "WHERE nspname LIKE 'conta\\_%' OR nspname LIKE 'legado%'"
        )).scalars().all()
        for schema in schemas:
            conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        conn.execute(text(
            "TRUNCATE public.webhook_routes, public.password_resets, public.platform_settings, "
            "public.admins, public.accounts RESTART IDENTITY CASCADE"
        ))
    signup_limiter.clear()
    login_failures.clear()
    for limiter in (password_reset.forgot_by_ip, password_reset.forgot_by_email, password_reset.reset_attempts):
        limiter.clear()


def entrar(email, senha=SENHA):
    r = client.post("/api/login", json={"email": email, "password": senha})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def criar_conta(email, nome="Dono", com_endpoint=True):
    """Cadastra uma conta nova pela tela de cadastro e devolve login + endereço de vendas."""
    r = client.post("/api/setup", json={
        "name": nome, "email": email, "password": SENHA, "confirm_password": SENHA,
    })
    assert r.status_code == 200, r.text
    auth = entrar(email)
    with engine.connect() as conn:
        account_id = conn.execute(
            text("SELECT account_id FROM public.admins WHERE email = :e"), {"e": email.lower()}
        ).scalar_one()
    conta = {"auth": auth, "account_id": account_id, "email": email}
    if com_endpoint:
        r = client.post("/api/platforms/webhooks", json={"platform": "api", "name": "Loja teste"}, headers=auth)
        assert r.status_code == 201, r.text
        conta["slug"] = r.json()["slug"]
        conta["endpoint_id"] = r.json()["id"]
        conta["url"] = f"/api/webhook/api/{conta['slug']}"
    return conta


def venda(external_id="PED-1", status="approved", amount=197.0, **extra):
    body = {
        "external_id": external_id,
        "status": status,
        "amount": amount,
        "product_external_id": "P1",
        "product_name": "Body Splash",
        "customer_email": "cliente@exemplo.com.br",
        "customer_name": "Cliente",
        "utm_source": "facebook",
        "utm_campaign": "camp-1",
    }
    body.update(extra)
    return body


def sessao(account_id=1):
    """Sessão do banco presa a uma conta (a primeira conta criada após reset_db é a 1)."""
    return account_session(account_id)
