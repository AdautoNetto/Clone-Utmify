"""Envio de e-mail por SMTP (ex.: Gmail com senha de app em smtp.gmail.com:465)."""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

logger = logging.getLogger(__name__)


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
            server.login(cfg.smtp_user, cfg.smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=20) as server:
            server.starttls(context=context)
            server.login(cfg.smtp_user, cfg.smtp_password)
            server.send_message(msg)


def send_email_quietly(cfg, to: str, subject: str, text: str) -> None:
    """Para tarefas em segundo plano: registra a falha em vez de derrubar a requisição."""
    try:
        send_email(cfg, to, subject, text)
    except Exception as e:
        logger.error(f"Falha ao enviar e-mail ({type(e).__name__}): {e}")
