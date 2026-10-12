"""
Administrador do sistema (tela Contas) e "Esqueci minha senha".
"""
import re

import pytest
from sqlalchemy import text

from api.auth import password_reset
from api.auth.ratelimit import SlidingWindow
from apoio import SENHA, client, criar_conta, entrar, reset_db, venda
from database.core.connection import engine

NOVA_SENHA = "outra-senha-456"


@pytest.fixture()
def contas():
    reset_db()
    return criar_conta("chefe@teste.com", "Chefe"), criar_conta("amigo@teste.com", "Amigo")


def _lista(auth):
    r = client.get("/api/platform/accounts", headers=auth)
    assert r.status_code == 200, r.text
    return {c["owner_email"]: c for c in r.json()}


# ── Quem administra ────────────────────────────────────────────────────────

def test_so_a_primeira_conta_administra_o_sistema(contas):
    chefe, amigo = contas
    assert client.get("/api/profile", headers=chefe["auth"]).json()["is_platform_admin"] is True
    assert client.get("/api/profile", headers=amigo["auth"]).json()["is_platform_admin"] is False
    for metodo, rota in (
        ("GET", "/api/platform/accounts"),
        ("PUT", f"/api/platform/accounts/{chefe['account_id']}/block"),
        ("POST", f"/api/platform/accounts/{chefe['account_id']}/delete"),
        ("POST", f"/api/platform/accounts/{chefe['account_id']}/reset-link"),
        ("GET", "/api/platform/email-settings"),
        ("PUT", "/api/platform/email-settings"),
        ("POST", "/api/platform/email-settings/test"),
    ):
        r = client.request(metodo, rota, json={"blocked": True, "confirm_email": "chefe@teste.com"},
                           headers=amigo["auth"])
        assert r.status_code == 403, f"{metodo} {rota} -> {r.status_code}"
    assert entrar("chefe@teste.com")  # nada mudou para a conta do chefe


def test_faturamento_soma_so_as_vendas_aprovadas(contas):
    chefe, amigo = contas
    client.post(amigo["url"], json=venda("PED-1", amount=100.0))
    client.post(amigo["url"], json=venda("PED-2", amount=50.0, status="pending"))
    client.post(amigo["url"], json=venda("PED-3", amount=40.0, status="refunded"))
    lista = _lista(chefe["auth"])
    assert lista["amigo@teste.com"]["revenue"] == 100.0
    assert lista["chefe@teste.com"]["revenue"] == 0.0


def test_lista_mostra_as_contas_com_numero_de_vendas(contas):
    chefe, amigo = contas
    client.post(amigo["url"], json=venda("PED-1"))
    client.post(amigo["url"], json=venda("PED-2"))
    lista = _lista(chefe["auth"])
    assert set(lista) == {"chefe@teste.com", "amigo@teste.com"}
    assert (lista["amigo@teste.com"]["sales"], lista["chefe@teste.com"]["sales"]) == (2, 0)
    assert lista["amigo@teste.com"]["last_sale_at"] is not None
    assert lista["chefe@teste.com"]["is_mine"] is True and lista["amigo@teste.com"]["is_mine"] is False
    assert "senha" not in str(lista).lower() and "password" not in str(lista).lower()


# ── Bloquear ───────────────────────────────────────────────────────────────

def test_bloquear_tira_o_acesso_mas_nao_perde_venda(contas):
    chefe, amigo = contas
    r = client.put(f"/api/platform/accounts/{amigo['account_id']}/block", json={"blocked": True}, headers=chefe["auth"])
    assert r.status_code == 200, r.text
    assert client.get("/api/sales/transactions", headers=amigo["auth"]).status_code == 401  # login antigo cai
    assert client.post("/api/login", json={"email": "amigo@teste.com", "password": SENHA}).status_code == 403
    assert client.post(amigo["url"], json=venda("PED-BLOQ")).status_code == 200  # a venda entra mesmo assim

    r = client.put(f"/api/platform/accounts/{amigo['account_id']}/block", json={"blocked": False}, headers=chefe["auth"])
    assert r.status_code == 200
    de_volta = entrar("amigo@teste.com")
    assert client.get("/api/sales/transactions", headers=de_volta).json()["total"] == 1


def test_nao_bloqueia_nem_exclui_a_propria_conta(contas):
    chefe, _ = contas
    r = client.put(f"/api/platform/accounts/{chefe['account_id']}/block", json={"blocked": True}, headers=chefe["auth"])
    assert r.status_code == 400
    r = client.post(f"/api/platform/accounts/{chefe['account_id']}/delete",
                    json={"confirm_email": "chefe@teste.com"}, headers=chefe["auth"])
    assert r.status_code == 400
    assert client.get("/api/profile", headers=chefe["auth"]).status_code == 200


# ── Excluir ────────────────────────────────────────────────────────────────

def test_excluir_exige_o_email_do_dono(contas):
    chefe, amigo = contas
    client.post(amigo["url"], json=venda("PED-1"))
    r = client.post(f"/api/platform/accounts/{amigo['account_id']}/delete",
                    json={"confirm_email": "errado@teste.com"}, headers=chefe["auth"])
    assert r.status_code == 400
    assert client.get("/api/sales/transactions", headers=amigo["auth"]).json()["total"] == 1


def test_excluir_apaga_a_conta_inteira_e_so_ela(contas):
    chefe, amigo = contas
    client.post(amigo["url"], json=venda("PED-AMIGO"))
    client.post(chefe["url"], json=venda("PED-CHEFE"))
    r = client.post(f"/api/platform/accounts/{amigo['account_id']}/delete",
                    json={"confirm_email": "AMIGO@teste.com"}, headers=chefe["auth"])
    assert r.status_code == 200, r.text

    assert client.get("/api/sales/transactions", headers=amigo["auth"]).status_code == 401
    assert client.post("/api/login", json={"email": "amigo@teste.com", "password": SENHA}).status_code == 401
    assert client.post(amigo["url"], json=venda("PED-DEPOIS")).status_code == 404
    with engine.connect() as conn:
        assert conn.execute(text(
            "SELECT count(*) FROM pg_namespace WHERE nspname = :s"),
            {"s": f"conta_{amigo['account_id']}"}).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM public.webhook_routes")).scalar_one() == 1
    assert set(_lista(chefe["auth"])) == {"chefe@teste.com"}
    assert client.get("/api/sales/transactions", headers=chefe["auth"]).json()["total"] == 1

    # o mesmo e-mail pode se cadastrar de novo e começa do zero
    de_novo = criar_conta("amigo@teste.com", "Amigo")
    assert de_novo["account_id"] != amigo["account_id"]
    assert client.get("/api/sales/transactions", headers=de_novo["auth"]).json()["total"] == 0


# ── Link de senha nova gerado pelo administrador ───────────────────────────

def _link(chefe, conta):
    r = client.post(f"/api/platform/accounts/{conta['account_id']}/reset-link", headers=chefe["auth"])
    assert r.status_code == 200, r.text
    assert r.json()["email"] == conta["email"]
    return re.search(r"token=([\w-]+)", r.json()["path"]).group(1)


def test_link_de_senha_nova_funciona_uma_vez_so(contas):
    chefe, amigo = contas
    token = _link(chefe, amigo)
    assert client.get(f"/api/password/reset/{token}").status_code == 200
    r = client.post(f"/api/password/reset/{token}", json={"password": NOVA_SENHA, "confirm_password": NOVA_SENHA})
    assert r.status_code == 200, r.text
    assert client.post("/api/login", json={"email": "amigo@teste.com", "password": SENHA}).status_code == 401
    assert entrar("amigo@teste.com", NOVA_SENHA)
    # usar de novo não funciona
    assert client.get(f"/api/password/reset/{token}").status_code == 404
    r = client.post(f"/api/password/reset/{token}", json={"password": SENHA, "confirm_password": SENHA})
    assert r.status_code == 404
    assert entrar("amigo@teste.com", NOVA_SENHA)


def test_link_vencido_inventado_ou_substituido_nao_funciona(contas):
    chefe, amigo = contas
    velho = _link(chefe, amigo)
    novo = _link(chefe, amigo)  # gerar outro invalida o anterior
    assert client.get(f"/api/password/reset/{velho}").status_code == 404
    assert client.get("/api/password/reset/codigo-inventado").status_code == 404
    with engine.begin() as conn:
        conn.exec_driver_sql("UPDATE public.password_resets SET expires_at = now() - interval '1 minute'")
    r = client.post(f"/api/password/reset/{novo}", json={"password": NOVA_SENHA, "confirm_password": NOVA_SENHA})
    assert r.status_code == 404
    assert entrar("amigo@teste.com", SENHA)  # senha antiga continua valendo


def test_senha_nova_segue_as_mesmas_regras_e_o_codigo_nao_fica_no_banco(contas):
    chefe, amigo = contas
    token = _link(chefe, amigo)
    r = client.post(f"/api/password/reset/{token}", json={"password": "curta", "confirm_password": "curta"})
    assert r.status_code == 400
    r = client.post(f"/api/password/reset/{token}", json={"password": NOVA_SENHA, "confirm_password": NOVA_SENHA + "x"})
    assert r.status_code == 400
    with engine.connect() as conn:
        guardado = conn.execute(text("SELECT token_hash FROM public.password_resets")).scalar_one()
    assert guardado != token and len(guardado) == 64
    assert client.get(f"/api/password/reset/{token}").status_code == 200  # erro de digitação não queima o link


# ── "Esqueci minha senha" por e-mail ───────────────────────────────────────

@pytest.fixture()
def caixa(monkeypatch):
    """Troca o envio de e-mail por uma caixa de saída falsa."""
    enviados = []
    monkeypatch.setattr(password_reset, "send_email",
                        lambda cfg, to, subject, body: enviados.append({"to": to, "subject": subject, "body": body}))
    return enviados


def _configurar_email(chefe):
    r = client.put("/api/platform/email-settings", headers=chefe["auth"], json={
        "smtp_host": "smtp.exemplo.com", "smtp_port": 465, "smtp_user": "robo@exemplo.com",
        "smtp_password": "abcd efgh ijkl mnop", "smtp_from_name": "Vale Tec",
        "public_url": "https://painel.exemplo.com/"})
    assert r.status_code == 200, r.text
    return r.json()


def test_sem_email_configurado_o_pedido_nao_cria_link(contas, caixa):
    r = client.post("/api/password/forgot", json={"email": "amigo@teste.com"})
    assert r.status_code == 200 and r.json() == {"email_enabled": False}
    assert caixa == []
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM public.password_resets")).scalar_one() == 0


def test_configuracao_de_email_nunca_devolve_a_senha(contas):
    chefe, _ = contas
    salvo = _configurar_email(chefe)
    assert salvo["configured"] is True and salvo["has_password"] is True
    assert salvo["public_url"] == "https://painel.exemplo.com"
    for resposta in (salvo, client.get("/api/platform/email-settings", headers=chefe["auth"]).json()):
        assert "smtp_password" not in resposta and "abcd" not in str(resposta)
    # salvar de novo sem digitar a senha mantém a que já estava
    r = client.put("/api/platform/email-settings", headers=chefe["auth"], json={
        "smtp_host": "smtp.exemplo.com", "smtp_port": 465, "smtp_user": "robo@exemplo.com",
        "smtp_password": "", "smtp_from_name": "Vale Tec", "public_url": "https://painel.exemplo.com"})
    assert r.json()["has_password"] is True
    r = client.put("/api/platform/email-settings", headers=chefe["auth"], json={"public_url": "javascript:alert(1)"})
    assert r.status_code == 400


def test_esqueci_minha_senha_manda_link_que_funciona(contas, caixa):
    chefe, _ = contas
    _configurar_email(chefe)
    r = client.post("/api/password/forgot", json={"email": "Amigo@Teste.com"})
    assert r.status_code == 200 and r.json() == {"email_enabled": True}
    assert len(caixa) == 1 and caixa[0]["to"] == "amigo@teste.com"
    link = re.search(r"https://painel\.exemplo\.com/reset\?token=([\w-]+)", caixa[0]["body"])
    assert link, caixa[0]["body"]
    r = client.post(f"/api/password/reset/{link.group(1)}", json={"password": NOVA_SENHA, "confirm_password": NOVA_SENHA})
    assert r.status_code == 200, r.text
    assert entrar("amigo@teste.com", NOVA_SENHA)


def test_resposta_igual_para_email_que_nao_existe_e_nada_e_enviado(contas, caixa):
    chefe, _ = contas
    _configurar_email(chefe)
    existe = client.post("/api/password/forgot", json={"email": "amigo@teste.com"})
    nao_existe = client.post("/api/password/forgot", json={"email": "ninguem@teste.com"})
    assert (existe.status_code, existe.json()) == (nao_existe.status_code, nao_existe.json())
    assert [e["to"] for e in caixa] == ["amigo@teste.com"]


def test_conta_bloqueada_nao_recebe_link(contas, caixa):
    chefe, amigo = contas
    _configurar_email(chefe)
    client.put(f"/api/platform/accounts/{amigo['account_id']}/block", json={"blocked": True}, headers=chefe["auth"])
    assert client.post("/api/password/forgot", json={"email": "amigo@teste.com"}).status_code == 200
    assert caixa == []


def test_limite_de_pedidos_por_email_e_por_conexao(contas, caixa, monkeypatch):
    chefe, _ = contas
    _configurar_email(chefe)
    monkeypatch.setattr(password_reset, "forgot_by_email", SlidingWindow(2, 3600))
    for _ in range(4):
        assert client.post("/api/password/forgot", json={"email": "amigo@teste.com"}).status_code == 200
    assert len(caixa) == 2  # não vira máquina de mandar e-mail para a mesma pessoa
    monkeypatch.setattr(password_reset, "forgot_by_ip", SlidingWindow(1, 3600))
    assert client.post("/api/password/forgot", json={"email": "x1@teste.com"}).status_code == 200
    assert client.post("/api/password/forgot", json={"email": "x2@teste.com"}).status_code == 429
