"""
Envio de e-mail: quando o servidor recusa a senha, o motivo tem que aparecer
(o Gmail fecha a conexão se o programa insistir num segundo método de login).
"""
import smtplib

import pytest

from apoio import client, criar_conta, reset_db
from integrations.email import smtp as smtp_module


class _GmailDeMentira:
    """Imita o Gmail: recusa a senha no PLAIN (535) e derruba a conexão se tentarem de novo."""
    tentativas = []

    def __init__(self, *a, **k):
        self.esmtp_features = {"auth": " LOGIN PLAIN XOAUTH2"}
        self.user = self.password = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def ehlo_or_helo_if_needed(self):
        pass

    def auth_plain(self, challenge=None):
        return f"\0{self.user}\0{self.password}"

    def auth(self, mechanism, authobject, **k):
        type(self).tentativas.append(mechanism)
        if len(type(self).tentativas) > 1:
            raise smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
        raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")

    def login(self, user, password):
        # o login() de verdade tenta PLAIN e depois LOGIN: a 2ª tentativa derruba a conexão
        self.user, self.password = user, password
        for mechanism in ("PLAIN", "LOGIN"):
            try:
                self.auth(mechanism, self.auth_plain)
            except smtplib.SMTPAuthenticationError:
                continue

    def send_message(self, msg):
        raise AssertionError("não deveria enviar sem ter entrado")


@pytest.fixture()
def chefe(monkeypatch):
    reset_db()
    _GmailDeMentira.tentativas = []
    monkeypatch.setattr(smtp_module.smtplib, "SMTP_SSL", _GmailDeMentira)
    conta = criar_conta("chefe@teste.com", "Chefe")
    r = client.put("/api/platform/email-settings", headers=conta["auth"], json={
        "smtp_host": "smtp.gmail.com", "smtp_port": 465, "smtp_user": "robo@gmail.com",
        "smtp_password": "senha-normal-da-conta", "smtp_from_name": "Vale Tec",
        "public_url": "https://painel.exemplo.com"})
    assert r.status_code == 200, r.text
    return conta


def test_senha_recusada_explica_que_precisa_de_senha_de_app(chefe):
    r = client.post("/api/platform/email-settings/test", headers=chefe["auth"])
    assert r.status_code == 400
    aviso = r.json()["detail"]
    assert "senha de app" in aviso and "Connection unexpectedly closed" not in aviso
    assert "senha-normal-da-conta" not in aviso  # a senha nunca aparece na mensagem
    assert _GmailDeMentira.tentativas == ["PLAIN"]  # uma tentativa só: não insiste
