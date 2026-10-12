from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
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
