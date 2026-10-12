"""
Testes do caminho crítico: webhook de venda → banco → métricas.
(Como rodar: ver tests/conftest.py.)
"""
import re

import pytest
from sqlalchemy import text

import app as app_module
from apoio import client, criar_conta, reset_db, sessao, venda as _venda
from database.core.connection import engine
from database.models.customer import Customer
from database.models.transaction import Transaction, TransactionStatus


@pytest.fixture()
def ctx():
    reset_db()
    return criar_conta("dono@teste.com")  # primeira conta do banco limpo = conta 1


def _tx(external_id):
    with sessao() as db:
        return db.query(Transaction).filter(Transaction.external_id == external_id).one()


def _customer(email="cliente@exemplo.com.br"):
    with sessao() as db:
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
    with sessao() as db:
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
    with sessao() as db:
        assert db.query(Transaction).count() == 0


def test_payload_bruto_fica_guardado(ctx):
    client.post(ctx["url"], json=_venda())
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT external_id, status FROM conta_1.webhook_events ORDER BY id"
        )).fetchall()
    assert [(r[0], r[1]) for r in rows] == [("PED-1", "processed")]


def test_payload_invalido_tambem_fica_guardado(ctx):
    r = client.post(ctx["url"], json={"status": "approved"})
    assert r.status_code == 422
    with engine.connect() as conn:
        status = conn.execute(text("SELECT status FROM conta_1.webhook_events")).scalar_one()
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
    with sessao() as db:
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


# ── Permissões: "viewer" (visualizador) é somente leitura ──────────────────

_ROTAS_PUBLICAS = {"/api/login", "/api/setup", "/api/setup/status", "/api/setup/invite/{token}",
                   "/api/webhook/{platform}/{slug}",
                   "/api/password/forgot", "/api/password/reset/{token}"}
_VIEWER_PODE = {("PUT", "/api/profile"), ("PUT", "/api/profile/password"),
                ("POST", "/api/gemini/chat"), ("POST", "/api/gemini/daily-report")}


def _login_com_papel(ctx, papel, email):
    r = client.post("/api/users/invite", json={"name": papel, "role": papel}, headers=ctx["auth"])
    assert r.status_code == 200, r.text
    token = r.json()["invite_token"]
    r = client.post(f"/api/setup/invite/{token}", json={
        "email": email, "password": "senha-teste-123", "confirm_password": "senha-teste-123"})
    assert r.status_code == 200, r.text
    r = client.post("/api/login", json={"email": email, "password": "senha-teste-123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_viewer_le_mas_nao_apaga_venda(ctx):
    client.post(ctx["url"], json=_venda())
    viewer = _login_com_papel(ctx, "viewer", "viewer@teste.com")
    assert client.get("/api/sales/transactions", headers=viewer).status_code == 200
    r = client.delete(f"/api/sales/transactions/{_tx('PED-1').id}", headers=viewer)
    assert r.status_code == 403
    assert _tx("PED-1").status == TransactionStatus.APPROVED  # continua lá
    r = client.put("/api/profile", json={"name": "Novo nome", "email": "viewer@teste.com"}, headers=viewer)
    assert r.status_code == 200, r.text


def test_admin_continua_podendo_apagar(ctx):
    client.post(ctx["url"], json=_venda())
    admin = _login_com_papel(ctx, "admin", "admin@teste.com")
    r = client.delete(f"/api/sales/transactions/{_tx('PED-1').id}", headers=admin)
    assert r.status_code == 204, r.text


def test_viewer_bloqueado_em_todas_as_rotas_de_escrita(ctx):
    """Varre o app inteiro: qualquer rota de escrita (atual ou futura) tem que negar o viewer."""
    viewer = _login_com_papel(ctx, "viewer", "viewer2@teste.com")
    testadas, vazou = 0, []
    # Lista oficial de rotas (OpenAPI): app.routes mudou de formato no FastAPI 0.14x
    for path, metodos in app_module.app.openapi()["paths"].items():
        if not path.startswith("/api") or path in _ROTAS_PUBLICAS:
            continue
        for method in (m.upper() for m in metodos):
            if method in ("GET", "HEAD", "OPTIONS") or (method, path) in _VIEWER_PODE:
                continue
            url = re.sub(r"\{[^}]+\}", "1", path)
            r = client.request(method, url, json={}, headers=viewer)
            testadas += 1
            if r.status_code != 403:
                vazou.append(f"{method} {path} -> {r.status_code}")
    assert testadas > 40
    assert vazou == []
