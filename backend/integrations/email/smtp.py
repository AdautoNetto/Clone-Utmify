"""Envio de e-mail por SMTP (ex.: Gmail com senha de app em smtp.gmail.com:465)."""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

logger = logging.getLogger(__name__)


def _login(server: smtplib.SMTP, user: str, password: str) -> None:
    """
    Entra usando só o método PLAIN quando o servidor oferece. O login() padrão,
    ao ter a senha recusada, tenta um segundo método; o Gmail fecha a conexão
    nessa hora e o motivo verdadeiro (535, senha não aceita) vira um
    "Connection unexpectedly closed" que não explica nada.
    """
    server.ehlo_or_helo_if_needed()
    offered = server.esmtp_features.get("auth", "").upper().split()
    if "PLAIN" in offered:
        server.user, server.password = user, password
        server.auth("PLAIN", server.auth_plain)
    else:
        server.login(user, password)


def describe_error(e: Exception) -> str:
    """Explica em português simples por que o envio falhou."""
    if isinstance(e, smtplib.SMTPAuthenticationError):
        return (
            "O servidor de e-mail não aceitou o e-mail e a senha. No Gmail, a senha normal "
            "da conta não funciona aqui: é preciso criar uma \"senha de app\" (16 letras) e colar essa."
        )
    if isinstance(e, (TimeoutError, ConnectionError, OSError)) and not isinstance(e, smtplib.SMTPException):
        return "Não consegui falar com o servidor de e-mail. Confira o endereço do servidor e a porta."
    return f"O servidor de e-mail recusou: {type(e).__name__}: {e}"[:300]


def send_email(cfg, to: str, subject: str, text: str) -> None:
    """Envia um e-mail de texto. Levanta exceção se o servidor de e-mail recusar."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((cfg.smtp_from_name or "Vale Tec", cfg.smtp_user))
    msg["To"] = to
    msg.set_content(text)

    context = ssl.create_default_context()
    if cfg.smtp_port == 465:
        with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=20, context=context) as server:
            _login(server, cfg.smtp_user, cfg.smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=20) as server:
            server.starttls(context=context)
            server.ehlo()
            _login(server, cfg.smtp_user, cfg.smtp_password)
            server.send_message(msg)


def send_email_quietly(cfg, to: str, subject: str, text: str) -> None:
    """Para tarefas em segundo plano: registra a falha em vez de derrubar a requisição."""
    try:
        send_email(cfg, to, subject, text)
    except Exception as e:
        logger.error(f"Falha ao enviar e-mail ({type(e).__name__}): {e}")
