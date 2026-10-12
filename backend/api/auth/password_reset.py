"""
"Esqueci minha senha": link de uso único para criar uma senha nova.

O link nasce de dois jeitos:
- a pessoa pede na tela de login e ele chega por e-mail (se o envio de e-mail
  estiver configurado pelo administrador do sistema);
- o administrador do sistema gera o link na tela Contas e manda para a pessoa.

No banco fica só o hash do código; o código em si aparece uma única vez.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.auth.ratelimit import SlidingWindow, client_ip
from api.auth.setup import check_new_password, hash_password
from api.platform.settings_store import load_email_config
from database.core.connection import get_db
from database.models.account import Account, PasswordReset
from database.models.admin import Admin
from integrations.email.smtp import send_email_quietly as send_email

router = APIRouter()

EMAILED_LINK_HOURS = 1
ADMIN_LINK_HOURS = 24

forgot_by_ip = SlidingWindow(10, 3600)
forgot_by_email = SlidingWindow(3, 3600)
reset_attempts = SlidingWindow(30, 3600)


class ForgotRequest(BaseModel):
    email: EmailStr


class ResetRequest(BaseModel):
    password: str
    confirm_password: str


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_reset_token(db: Session, admin: Admin, hours: int) -> str:
    """Gera o código (devolvido só aqui) e invalida os anteriores dessa pessoa."""
    db.query(PasswordReset).filter(PasswordReset.admin_id == admin.id).delete()
    token = secrets.token_urlsafe(32)
    db.add(PasswordReset(
        admin_id=admin.id,
        token_hash=_hash(token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
    ))
    return token


def _valid_reset(db: Session, token: str) -> PasswordReset | None:
    row = db.query(PasswordReset).filter(PasswordReset.token_hash == _hash(token)).first()
    if not row or row.used_at is not None or row.expires_at < datetime.now(timezone.utc):
        return None
    return row


@router.post("/password/forgot")
def forgot_password(
    data: ForgotRequest, request: Request, background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    A resposta é sempre a mesma, exista ou não conta com esse e-mail (para não
    revelar quem tem cadastro). `email_enabled` só diz se o sistema envia e-mail.
    """
    ip = client_ip(request)
    if forgot_by_ip.blocked(ip):
        raise HTTPException(status_code=429, detail="Muitos pedidos. Tente de novo em 1 hora.")
    forgot_by_ip.add(ip)

    cfg = load_email_config(db)
    email = data.email.strip().lower()
    if cfg.configured and not forgot_by_email.blocked(email):
        forgot_by_email.add(email)
        admin = db.query(Admin).filter(func.lower(Admin.email) == email).first()
        if admin and admin.password_hash and admin.account_id is not None:
            account = db.get(Account, admin.account_id)
            if account and not account.blocked:
                token = create_reset_token(db, admin, EMAILED_LINK_HOURS)
                db.commit()
                link = f"{cfg.public_url}/reset?token={token}"
                background.add_task(
                    send_email, cfg, admin.email,
                    "Criar uma senha nova",
                    f"Olá, {admin.name}.\n\n"
                    f"Recebemos um pedido para criar uma senha nova para a sua conta.\n"
                    f"Abra este link (vale por {EMAILED_LINK_HOURS} hora e só funciona uma vez):\n\n"
                    f"{link}\n\n"
                    f"Se não foi você que pediu, ignore este e-mail: a sua senha continua a mesma.\n",
                )
    return {"email_enabled": cfg.configured}


@router.get("/password/reset/{token}")
def check_reset_token(token: str, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    if reset_attempts.blocked(ip):
        raise HTTPException(status_code=429, detail="Muitas tentativas. Tente de novo em 1 hora.")
    if not _valid_reset(db, token):
        reset_attempts.add(ip)
        raise HTTPException(status_code=404, detail="Link inválido ou vencido. Peça um novo.")
    return {"valid": True}


@router.post("/password/reset/{token}")
def reset_password(token: str, data: ResetRequest, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    if reset_attempts.blocked(ip):
        raise HTTPException(status_code=429, detail="Muitas tentativas. Tente de novo em 1 hora.")
    row = _valid_reset(db, token)
    if not row:
        reset_attempts.add(ip)
        raise HTTPException(status_code=404, detail="Link inválido ou vencido. Peça um novo.")

    check_new_password(data.password, data.confirm_password)

    admin = db.get(Admin, row.admin_id)
    admin.password_hash = hash_password(data.password)
    admin.token_version = (admin.token_version or 0) + 1  # quem estava logado com a senha antiga cai
    row.used_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Senha criada. Já pode entrar."}
