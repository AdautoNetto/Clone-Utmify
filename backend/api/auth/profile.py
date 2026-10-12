from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import bcrypt

from database.core.connection import get_db
from sqlalchemy import func
from database.models.admin import Admin
from api.auth.setup import check_new_password, hash_password
from api.auth.login import issue_token
from api.auth.deps import get_current_user

router = APIRouter()

class ProfileUpdateRequest(BaseModel):
    name: str
    email: EmailStr

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

@router.get("/profile")
def get_profile(current_user: Admin = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.value,
        "is_platform_admin": bool(current_user.is_platform_admin),
    }

@router.put("/profile")
def update_profile(data: ProfileUpdateRequest, current_user: Admin = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if email is already taken by another admin
    email = data.email.strip().lower()
    if email != (current_user.email or "").lower():
        existing = db.query(Admin).filter(
            func.lower(Admin.email) == email, Admin.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Este e-mail já está em uso")
    
    current_user.name = data.name
    current_user.email = email
    db.commit()
    db.refresh(current_user)
    
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.value,
        "is_platform_admin": bool(current_user.is_platform_admin),
    }

@router.put("/profile/password")
def change_password(data: PasswordChangeRequest, current_user: Admin = Depends(get_current_user), db: Session = Depends(get_db)):
    # Pede a senha atual: uma sessão esquecida aberta não basta para tomar a conta
    try:
        current_ok = bcrypt.checkpw(
            data.current_password.encode("utf-8"), (current_user.password_hash or "").encode("utf-8")
        )
    except ValueError:
        current_ok = False
    if not current_ok:
        raise HTTPException(status_code=400, detail="A senha atual não confere")

    check_new_password(data.new_password, data.confirm_password)
    current_user.password_hash = hash_password(data.new_password)
    current_user.token_version = (current_user.token_version or 0) + 1  # derruba as outras sessões
    db.commit()
    db.refresh(current_user)

    # Este navegador continua logado com um login novo
    return {"message": "Senha atualizada com sucesso", "access_token": issue_token(current_user)}
