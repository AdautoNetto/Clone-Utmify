"""
Consulta e reprocessamento dos webhooks brutos (tabela webhook_events).

Se um webhook falhar (status "failed"), o payload continua salvo e pode ser
reprocessado aqui depois de corrigida a causa — a venda não se perde.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from database.core.connection import get_db
from database.models.admin import UserRole
from database.models.webhook_event import WebhookEvent
from api.auth.deps import require_role
from api.webhook.receive import run_stored_webhook

router = APIRouter(prefix="/webhook-events", tags=["webhook-events"])


@router.get("")
def list_webhook_events(
    status: str | None = Query(None, description="received | processed | ignored | rejected | failed"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _=Depends(require_role(UserRole.owner, UserRole.admin)),
):
    query = db.query(WebhookEvent)
    if status:
        query = query.filter(WebhookEvent.status == status)
    rows = query.order_by(WebhookEvent.id.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "platform": r.platform,
            "webhook_slug": r.webhook_slug,
            "external_id": r.external_id,
            "status": r.status,
            "error": r.error,
            "attempts": r.attempts,
            "received_at": r.received_at,
            "processed_at": r.processed_at,
        }
        for r in rows
    ]


@router.post("/{event_id}/reprocess")
async def reprocess_webhook_event(
    event_id: int,
    _=Depends(require_role(UserRole.owner, UserRole.admin)),
):
    return await run_in_threadpool(run_stored_webhook, event_id)
