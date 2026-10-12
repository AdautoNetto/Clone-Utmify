from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import bcrypt

from database.core.connection import get_db
from sqlalchemy import func
from database.models.admin import Admin
from api.auth.setup import check_new_password, hash_password
from api.auth.deps import get_current_user

router = APIRouter()

class ProfileUpdateRequest(BaseModel):
    name: str
    email: EmailStr

class PasswordChangeRequest(BaseModel):
    new_password: str
    confirm_password: str

@router.get("/profile")
def get_profile(current_user: Admin = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.value,
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
            raise HTTPException(status_code=400, detail="Email already registered")
    
    current_user.name = data.name
    current_user.email = email
    db.commit()
    db.refresh(current_user)
    
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email
    }

@router.put("/profile/password")
def change_password(data: PasswordChangeRequest, current_user: Admin = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="As senhas não coincidem")
        
    check_new_password(data.new_password, data.confirm_password)
    current_user.password_hash = hash_password(data.new_password)
    db.commit()
    
    return {"message": "Senha atualizada com sucesso"}
