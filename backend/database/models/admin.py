import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from database.core.connection import Base
from database.core.timezone import CREATED_AT_DEFAULT


class UserRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    viewer = "viewer"


class Admin(Base):
    """Usuário (login). Tabela global: o e-mail é único no sistema inteiro."""
    __tablename__ = "admins"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Conta a que o usuário pertence (o dono e as pessoas que ele convidou)
    account_id = Column(Integer, ForeignKey("public.accounts.id"), nullable=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(
        Enum(UserRole, name="userrole", schema="public"),
        nullable=False, default=UserRole.admin,
    )
    invite_token = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime, server_default=CREATED_AT_DEFAULT)
