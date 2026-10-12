import logging
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import bcrypt
from database.core.connection import get_db
from database.core.bootstrap import SchemaAlreadyExists, provision_schema
from database.core.tenancy import schema_for
from database.models.account import Account
from database.models.admin import Admin, UserRole
from api.auth.ratelimit import SlidingWindow, client_ip

logger = logging.getLogger(__name__)

router = APIRouter()

MIN_PASSWORD_LENGTH = 8

# Cadastro aberto: qualquer pessoa cria a própria conta (como na Utmify).
# SIGNUP_ENABLED=0 fecha o cadastro; MAX_ACCOUNTS limita o total (servidor pequeno).
SIGNUP_ENABLED = os.getenv("SIGNUP_ENABLED", "1").strip() not in ("0", "false", "False", "")
MAX_ACCOUNTS = int(os.getenv("MAX_ACCOUNTS", "300"))
signup_limiter = SlidingWindow(int(os.getenv("SIGNUP_MAX_PER_HOUR", "20")), 3600)


class SetupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    confirm_password: str


class InviteSetupRequest(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str


class SetupStatusResponse(BaseModel):
    is_configured: bool
    signup_enabled: bool = True


class InviteInfoResponse(BaseModel):
    name: str
    role: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_new_password(password: str, confirm: str) -> None:
    if password != confirm:
        raise HTTPException(status_code=400, detail="As senhas não coincidem")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"A senha deve ter pelo menos {MIN_PASSWORD_LENGTH} caracteres",
        )
    if len(password.encode("utf-8")) > 72:  # limite do bcrypt
        raise HTTPException(status_code=400, detail="A senha deve ter no máximo 72 caracteres")


@router.get("/setup/status", response_model=SetupStatusResponse)
def setup_status():
    # Multi-conta: não existe mais "primeira configuração"; o painel sempre abre no login
    return {"is_configured": True, "signup_enabled": SIGNUP_ENABLED}


@router.get("/setup/invite/{token}", response_model=InviteInfoResponse)
def get_invite_info(token: str, db: Session = Depends(get_db)):
    """Return name and role for an invite token (no auth needed)."""
    invite = db.query(Admin).filter(Admin.invite_token == token).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Convite inválido ou expirado")
    return {"name": invite.name, "role": invite.role.value}


@router.post("/setup")
def create_account(data: SetupRequest, request: Request, db: Session = Depends(get_db)):
    """Cadastro: cria uma conta nova (com o compartimento de dados dela) e o usuário dono."""
    if not SIGNUP_ENABLED:
        raise HTTPException(status_code=403, detail="O cadastro de novas contas está fechado")

    ip = client_ip(request)
    if signup_limiter.blocked(ip):
        raise HTTPException(
            status_code=429,
            detail="Muitas contas criadas a partir desta conexão. Tente de novo em 1 hora.",
        )

    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Informe o seu nome")
    check_new_password(data.password, data.confirm_password)

    email = data.email.strip().lower()
    if db.query(Admin).filter(func.lower(Admin.email) == email).first():
        raise HTTPException(status_code=400, detail="Este e-mail já tem conta. Faça login.")

    if db.query(Account).count() >= MAX_ACCOUNTS:
        raise HTTPException(status_code=403, detail="Limite de contas do sistema atingido")

    try:
        account = Account(name=name[:100])
        db.add(account)
        db.flush()
        db.add(Admin(
            name=name[:100],
            email=email,
            password_hash=hash_password(data.password),
            role=UserRole.owner,
            account_id=account.id,
        ))
        db.flush()
        # Mesma transação: ou a conta nasce completa (usuário + tabelas), ou nada fica
        provision_schema(db.connection(), schema_for(account.id), new_account=True)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Este e-mail já tem conta. Faça login.")
    except SchemaAlreadyExists as e:
        db.rollback()
        # O número de conta já foi gasto: a próxima tentativa recebe outro e funciona
        logger.error(f"Cadastro recusado: o compartimento {e} já existia (sobra de restauração?)")
        raise HTTPException(status_code=503, detail="Não foi possível criar a conta agora. Tente de novo.")

    signup_limiter.add(ip)
    return {"message": "Conta criada com sucesso"}


@router.post("/setup/invite/{token}")
def complete_invite(token: str, data: InviteSetupRequest, db: Session = Depends(get_db)):
    """Complete an invite – convidado sets email + password."""
    invite = db.query(Admin).filter(Admin.invite_token == token).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Convite inválido ou expirado")

    check_new_password(data.password, data.confirm_password)

    email = data.email.strip().lower()
    # Check if email is already taken
    existing = db.query(Admin).filter(func.lower(Admin.email) == email, Admin.id != invite.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já está em uso")

    invite.email = email
    invite.password_hash = hash_password(data.password)
    invite.invite_token = None  # consume the token
    db.commit()

    return {"message": "Conta criada com sucesso"}
