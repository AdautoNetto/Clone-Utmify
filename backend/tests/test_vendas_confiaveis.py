"""
Testes do caminho crítico: webhook de venda → banco → métricas.

Rodam contra um Postgres de verdade (o app usa recursos do Postgres).
Use um banco VAZIO e descartável — os testes apagam tudo dele:

    TEST_DATABASE_URL=postgresql://postgres@localhost:5432/logpose_test pytest backend/tests -q
"""
import os
import uuid

import pytest

TEST_DB = os.getenv("TEST_DATABASE_URL")
if not TEST_DB:
    pytest.skip("TEST_DATABASE_URL não definido", allow_module_level=True)

os.environ["DATABASE_URL"] = TEST_DB
os.environ.setdefault("SECRET_KEY", "chave-so-para-teste-" + uuid.uuid4().hex)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import app as app_module  # noqa: E402
from database.core.connection import SessionLocal, engine  # noqa: E402
from database.models.customer import Customer  # noqa: E402
from database.models.transaction import Transaction, TransactionStatus  # noqa: E402

client = TestClient(app_module.app)


def _reset_db():
    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE refund_reasons, customer_products, recoveries, transactions, "
            "customers, product_aliases, checkouts, order_bumps, upsells, products, "
            "webhook_endpoints, admins RESTART IDENTITY CASCADE"
        ))
        conn.execute(text(
            "DO $$ BEGIN IF to_regclass('webhook_events') IS NOT NULL "
            "THEN TRUNCATE webhook_events RESTART IDENTITY; END IF; END $$;"
        ))


@pytest.fixture()
def ctx():
    _reset_db()
    r = client.post("/api/setup", json={
        "name": "Dono", "email": "dono@teste.com",
        "password": "senha-teste-123", "confirm_password": "senha-teste-123",
    })
    assert r.status_code == 200, r.text
    r = client.post("/api/login", json={"email": "dono@teste.com", "password": "senha-teste-123"})
    token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/platforms/webhooks", json={"platform": "api", "name": "Loja teste"}, headers=auth)
    assert r.status_code == 201, r.text
    return {"auth": auth, "url": f"/api/webhook/api/{r.json()['slug']}"}


def _venda(external_id="PED-1", status="approved", amount=197.0, **extra):
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


def _tx(external_id):
    with SessionLocal() as db:
        return db.query(Transaction).filter(Transaction.external_id == external_id).one()


def _customer(email="cliente@exemplo.com.br"):
    with SessionLocal() as db:
        return db.query(Customer).filter(Customer.email == email).one()


def test_venda_aprovada_entra_no_banco(ctx):
    r = client.post(ctx["url"], json=_venda())
    assert r.status_code == 200, r.text
    tx = _tx("PED-1")
    assert tx.status == TransactionStatus.APPROVED
    assert tx.amount == 197.0
    assert tx.utm_campaign == "camp-1"


def test_webhook_repetido_nao_duplica(ctx):
    for _ in range(3):
        assert client.post(ctx["url"], json=_venda()).status_code == 200
    with SessionLocal() as db:
        assert db.query(Transaction).count() == 1
    c = _customer()
    assert c.total_orders == 1
    assert c.total_spent == 197.0


def test_evento_atrasado_nao_desfaz_venda_aprovada(ctx):
    """Pix: 'pending' chega DEPOIS do 'approved' (reenvio/atraso). A venda não pode sumir."""
    client.post(ctx["url"], json=_venda(status="pending"))
    client.post(ctx["url"], json=_venda(status="approved"))
    client.post(ctx["url"], json=_venda(status="pending"))
    assert _tx("PED-1").status == TransactionStatus.APPROVED
    assert _customer().total_orders == 1


def test_aprovado_atrasado_nao_desfaz_reembolso(ctx):
    client.post(ctx["url"], json=_venda(status="approved"))
    client.post(ctx["url"], json=_venda(status="refunded"))
    client.post(ctx["url"], json=_venda(status="approved"))
    assert _tx("PED-1").status == TransactionStatus.REFUNDED
    c = _customer()
    assert c.total_orders == 0
    assert c.total_spent == 0.0


def test_valor_e_utm_preenchidos_quando_pendente_vira_aprovado(ctx):
    client.post(ctx["url"], json=_venda(status="pending", amount=0, utm_campaign=None))
    client.post(ctx["url"], json=_venda(status="approved", amount=197.0, utm_campaign="camp-1"))
    tx = _tx("PED-1")
    assert tx.status == TransactionStatus.APPROVED
    assert tx.amount == 197.0
    assert tx.utm_campaign == "camp-1"


def test_sem_external_id_e_recusado_e_nao_mistura_vendas(ctx):
    r1 = client.post(ctx["url"], json=_venda(external_id="", customer_email="a@exemplo.com.br"))
    r2 = client.post(ctx["url"], json=_venda(external_id="", customer_email="b@exemplo.com.br"))
    assert r1.status_code == 422
    assert r2.status_code == 422
    with SessionLocal() as db:
        assert db.query(Transaction).count() == 0


def test_payload_bruto_fica_guardado(ctx):
    client.post(ctx["url"], json=_venda())
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT external_id, status FROM webhook_events ORDER BY id"
        )).fetchall()
    assert [(r[0], r[1]) for r in rows] == [("PED-1", "processed")]


def test_payload_invalido_tambem_fica_guardado(ctx):
    r = client.post(ctx["url"], json={"status": "approved"})
    assert r.status_code == 422
    with engine.connect() as conn:
        status = conn.execute(text("SELECT status FROM webhook_events")).scalar_one()
    assert status == "rejected"


def test_apagar_venda_com_motivo_de_reembolso(ctx):
    client.post(ctx["url"], json=_venda(status="refunded"))
    tx_id = _tx("PED-1").id
    r = client.post("/api/refunds/reasons", json={"transaction_id": tx_id, "reason_code": "x"}, headers=ctx["auth"])
    assert r.status_code == 200, r.text
    r = client.delete(f"/api/sales/transactions/{tx_id}", headers=ctx["auth"])
    assert r.status_code == 204, r.text


def test_apagar_venda_atualiza_total_do_cliente(ctx):
    client.post(ctx["url"], json=_venda(external_id="PED-1"))
    client.post(ctx["url"], json=_venda(external_id="PED-2", amount=50.0))
    assert _customer().total_spent == 247.0
    r = client.delete(f"/api/sales/transactions/{_tx('PED-1').id}", headers=ctx["auth"])
    assert r.status_code == 204
    c = _customer()
    assert c.total_orders == 1
    assert c.total_spent == 50.0


def test_health(ctx):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"


def test_falha_interna_guarda_evento_e_reprocessa(ctx, monkeypatch):
    """Banco/código falhou no meio: responde 500 (plataforma reenvia) e nada se perde."""
    import api.webhook.receive as receive

    def quebra(*a, **k):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(receive, "process_webhook_event", quebra)
    r = client.post(ctx["url"], json=_venda())
    assert r.status_code == 500
    with SessionLocal() as db:
        assert db.query(Transaction).count() == 0

    r = client.get("/api/webhook-events?status=failed", headers=ctx["auth"])
    assert r.status_code == 200
    falhas = r.json()
    assert len(falhas) == 1 and falhas[0]["external_id"] == "PED-1"

    monkeypatch.undo()
    r = client.post(f"/api/webhook-events/{falhas[0]['id']}/reprocess", headers=ctx["auth"])
    assert r.status_code == 200, r.text
    assert _tx("PED-1").status == TransactionStatus.APPROVED
    r = client.get("/api/webhook-events?status=processed", headers=ctx["auth"])
    assert [e["id"] for e in r.json()] == [falhas[0]["id"]]


def test_eventos_exigem_login(ctx):
    assert client.get("/api/webhook-events").status_code in (401, 403)
