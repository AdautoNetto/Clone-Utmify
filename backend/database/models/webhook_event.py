from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from database.core.connection import Base
from database.core.timezone import CREATED_AT_DEFAULT


class WebhookEvent(Base):
    """
    Registro bruto de cada webhook recebido, gravado ANTES do processamento.
    Garante que nenhuma venda se perde: se o processamento falhar, o payload
    continua aqui e pode ser reprocessado (POST /api/webhook-events/{id}/reprocess).

    status: received | processed | ignored | rejected | failed
    """
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False)
    webhook_slug = Column(String(50), nullable=False, index=True)
    external_id = Column(String(255), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="received", index=True)
    error = Column(Text, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    payload = Column(JSON, nullable=True)
    received_at = Column(DateTime, server_default=CREATED_AT_DEFAULT, index=True)
    processed_at = Column(DateTime, nullable=True)
