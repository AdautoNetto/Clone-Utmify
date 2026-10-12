from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import bcrypt
from database.core.connection import get_db
from database.models.account import Account
from database.models.admin import Admin
from api.auth.token import create_access_token
from api.auth.ratelimit import SlidingWindow, client_ip

router = APIRouter()

# 10 senhas erradas em 15 min para o mesmo e-mail a partir da mesma conexão → espera
login_failures = SlidingWindow(10, 15 * 60)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


def issue_token(admin: Admin) -> str:
    return create_access_token({
        "sub": str(admin.id),
        "acc": admin.account_id,  # conta: define quais dados o login enxerga
        "ver": admin.token_version or 0,  # trocar a senha invalida os logins anteriores
        "email": admin.email,
        "role": admin.role.value,
    })


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    key = f"{client_ip(request)}|{email}"
    if login_failures.blocked(key):
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas. Espere 15 minutos e tente de novo.",
        )

    admin = db.query(Admin).filter(func.lower(Admin.email) == email).first()

    ok = False
    if admin and admin.password_hash and admin.account_id is not None:
        try:
            ok = bcrypt.checkpw(data.password.encode("utf-8"), admin.password_hash.encode("utf-8"))
        except ValueError:
            ok = False
    if not ok:
        login_failures.add(key)
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")

    account = db.get(Account, admin.account_id)
    if account is None or account.blocked:
        raise HTTPException(
            status_code=403,
            detail="Esta conta está bloqueada. Fale com quem administra o sistema.",
        )

    login_failures.clear(key)
    token = issue_token(admin)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": admin.id,
            "name": admin.name,
            "email": admin.email,
            "role": admin.role.value,
            "is_platform_admin": bool(admin.is_platform_admin),
        },
    }
