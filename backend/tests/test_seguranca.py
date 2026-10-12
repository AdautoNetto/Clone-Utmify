"""
Passada de segurança para abrir ao público: chaves de integração, sessões,
cabeçalhos, documentação fechada e primeiros passos.
"""
import pytest

from apoio import SENHA, client, criar_conta, entrar, reset_db, sessao, venda
from database.models.facebook_account import FacebookAccount
from database.models.gemini_account import GeminiAccount
from database.models.stripe_account import StripeAccount

CHAVE = "chave-de-teste-ABCDEFGH-1234"
NOVA = "outra-senha-456"


@pytest.fixture()
def conta():
    reset_db()
    return criar_conta("dono@teste.com")


def _convidar(conta, papel, email):
    r = client.post("/api/users/invite", json={"name": papel, "role": papel}, headers=conta["auth"])
    r2 = client.post(f"/api/setup/invite/{r.json()['invite_token']}", json={
        "email": email, "password": SENHA, "confirm_password": SENHA})
    assert r2.status_code == 200, r2.text
    return r.json()["id"], entrar(email)


# ── Chaves de integração ───────────────────────────────────────────────────

def test_chaves_nao_voltam_inteiras_para_o_navegador(conta):
    r = client.post("/api/gemini/accounts", json={"name": "G", "api_key": CHAVE, "model": "m"}, headers=conta["auth"])
    assert r.status_code == 201, r.text
    assert CHAVE not in r.text and r.json()["api_key"].endswith(CHAVE[-4:])
    r = client.post("/api/vturb/accounts", json={"name": "V", "api_key": CHAVE}, headers=conta["auth"])
    assert r.status_code == 201 and CHAVE not in r.text
    with sessao() as db:
        db.add(StripeAccount(name="S", api_key=CHAVE))
        db.commit()
        assert db.query(GeminiAccount).one().api_key == CHAVE  # no servidor continua inteira (a IA precisa dela)
    for rota in ("/api/gemini/accounts", "/api/vturb/accounts", "/api/stripe/accounts"):
        r = client.get(rota, headers=conta["auth"])
        assert r.status_code == 200 and len(r.json()) == 1, rota
        assert CHAVE not in r.text, rota


def test_visualizador_nao_recebe_token_do_facebook(conta):
    with sessao() as db:
        db.add(FacebookAccount(label="Conta", account_id="act_1", access_token=CHAVE))
        db.commit()
    _, viewer = _convidar(conta, "viewer", "viewer@teste.com")
    r = client.get("/api/facebook/accounts", headers=viewer)
    assert r.status_code == 200 and CHAVE not in r.text
    # quem administra a conta continua recebendo (a tela usa para sincronizar/trocar)
    assert CHAVE in client.get("/api/facebook/accounts", headers=conta["auth"]).text


def test_chave_do_gemini_nao_vai_mais_na_url(conta):
    r = client.get(f"/api/gemini/models?api_key={CHAVE}", headers=conta["auth"])
    assert r.status_code == 405


# ── Sessões e senha ────────────────────────────────────────────────────────

def test_trocar_senha_pede_a_atual_e_derruba_as_outras_sessoes(conta):
    outra_sessao = entrar("dono@teste.com")
    corpo = {"current_password": "errada-errada", "new_password": NOVA, "confirm_password": NOVA}
    assert client.put("/api/profile/password", json=corpo, headers=conta["auth"]).status_code == 400
    assert entrar("dono@teste.com")  # nada mudou

    corpo["current_password"] = SENHA
    r = client.put("/api/profile/password", json=corpo, headers=conta["auth"])
    assert r.status_code == 200, r.text
    novo = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/profile", headers=novo).status_code == 200          # este navegador segue logado
    assert client.get("/api/profile", headers=conta["auth"]).status_code == 401   # login antigo caiu
    assert client.get("/api/profile", headers=outra_sessao).status_code == 401    # o do outro aparelho também
    assert client.post("/api/login", json={"email": "dono@teste.com", "password": SENHA}).status_code == 401
    assert entrar("dono@teste.com", NOVA)


def test_dono_redefinir_senha_do_convidado_derruba_a_sessao_dele(conta):
    membro_id, membro = _convidar(conta, "admin", "membro@teste.com")
    r = client.put(f"/api/users/{membro_id}/reset-password",
                   json={"new_password": NOVA, "confirm_password": NOVA}, headers=conta["auth"])
    assert r.status_code == 200, r.text
    assert client.get("/api/profile", headers=membro).status_code == 401
    assert entrar("membro@teste.com", NOVA)


def test_senha_nova_pelo_link_derruba_quem_estava_logado():
    reset_db()
    chefe = criar_conta("chefe@teste.com")
    amigo = criar_conta("amigo@teste.com")
    r = client.post(f"/api/platform/accounts/{amigo['account_id']}/reset-link", headers=chefe["auth"])
    token = r.json()["path"].split("token=")[1]
    r = client.post(f"/api/password/reset/{token}", json={"password": NOVA, "confirm_password": NOVA})
    assert r.status_code == 200, r.text
    assert client.get("/api/profile", headers=amigo["auth"]).status_code == 401
    assert client.get("/api/profile", headers=chefe["auth"]).status_code == 200  # as outras contas não são afetadas


# ── Cabeçalhos, documentação e CORS ────────────────────────────────────────

def test_cabecalhos_de_seguranca_em_toda_resposta(conta):
    # "/" e "/login" são a página do painel (ou 404 sem o painel montado): também têm que vir protegidas
    for r in (client.get("/api/health"), client.get("/api/sales/transactions"),
              client.get("/api/sales/transactions", headers=conta["auth"]),
              client.get("/"), client.get("/login")):
        h = r.headers
        assert h["x-content-type-options"] == "nosniff"
        assert h["x-frame-options"] == "DENY"
        assert h["referrer-policy"] == "same-origin"
        assert "max-age" in h["strict-transport-security"]
        csp = h["content-security-policy"]
        assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp and "object-src 'none'" in csp
        assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]  # script embutido não roda


def test_painel_na_vercel_usa_a_mesma_politica_do_servidor():
    """deploy/vercel-config.js repete a lista do servidor: as duas têm que continuar iguais."""
    import os
    from api.security_headers import build_csp
    caminho = os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "vercel-config.js")
    with open(caminho, encoding="utf-8") as f:
        js = f.read()
    for diretiva in build_csp([]).split("; "):
        assert f'"{diretiva}' in js, diretiva


def test_documentacao_automatica_fica_fechada(conta):
    for rota in ("/docs", "/redoc", "/openapi.json"):
        r = client.get(rota)
        # 404 sem o painel montado; com ele, cai na tela do painel. Nunca na lista de rotas.
        assert "swagger" not in r.text.lower() and "redoc" not in r.text.lower(), rota
        assert '"paths"' not in r.text, rota


def test_cors_nao_aceita_credenciais_de_outro_site(conta):
    r = client.options("/api/sales/transactions", headers={
        "Origin": "https://site-malicioso.exemplo", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-credentials" not in r.headers


# ── Primeiros passos ───────────────────────────────────────────────────────

def test_primeiros_passos_acompanham_a_conta():
    reset_db()
    nova = criar_conta("nova@teste.com", com_endpoint=False)
    assert client.get("/api/onboarding/status").status_code in (401, 403)
    assert client.get("/api/onboarding/status", headers=nova["auth"]).json() == {
        "has_endpoint": False, "has_sale": False, "has_facebook": False}
    r = client.post("/api/platforms/webhooks", json={"platform": "api", "name": "Loja"}, headers=nova["auth"])
    passo = client.get("/api/onboarding/status", headers=nova["auth"]).json()
    assert (passo["has_endpoint"], passo["has_sale"]) == (True, False)
    assert client.post(f"/api/webhook/api/{r.json()['slug']}", json=venda()).status_code == 200
    assert client.get("/api/onboarding/status", headers=nova["auth"]).json()["has_sale"] is True
