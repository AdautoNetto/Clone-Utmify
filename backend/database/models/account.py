from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, text
from database.core.connection import Base
from database.core.timezone import CREATED_AT_DEFAULT


class Account(Base):
    """
    Uma conta = um cliente do sistema (quem se cadastrou). Os dados de negócio
    de cada conta ficam num schema próprio (ver database/core/tenancy.py).
    """
    __tablename__ = "accounts"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    # Bloqueada pelo administrador do sistema: ninguém da conta entra (as vendas continuam chegando)
    blocked = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at = Column(DateTime, server_default=CREATED_AT_DEFAULT)


class WebhookRoute(Base):
    """
    Diz de qual conta é cada endereço de webhook (slug). É por aqui que uma
    venda recebida (sem login) chega ao compartimento da conta certa.
    """
    __tablename__ = "webhook_routes"
    __table_args__ = {"schema": "public"}

    slug = Column(String(50), primary_key=True)
    account_id = Column(
        Integer, ForeignKey("public.accounts.id", ondelete="CASCADE"), nullable=False
    )


class PasswordReset(Base):
    """Link de uso único para criar uma senha nova. Guarda só o hash do código."""
    __tablename__ = "password_resets"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(
        Integer, ForeignKey("public.admins.id", ondelete="CASCADE"), nullable=False
    )
    token_hash = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, server_default=CREATED_AT_DEFAULT)


class PlatformSetting(Base):
    """Configuração do sistema inteiro (ex.: envio de e-mail). Chave → valor."""
    __tablename__ = "platform_settings"
    __table_args__ = {"schema": "public"}

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
