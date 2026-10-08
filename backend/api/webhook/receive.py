import json
import logging
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from database.core.connection import SessionLocal
from database.core.timezone import now_sp
from database.models.webhook_endpoint import WebhookEndpoint, WebhookPlatform
from database.models.webhook_event import WebhookEvent
from integrations.webhook.kiwify import parse_kiwify_webhook
from integrations.webhook.payt import parse_payt_webhook
from integrations.webhook.api_direct import parse_api_webhook
from integrations.webhook.processor import process_webhook_event
from integrations.webhook.test_emails import is_test_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook-receiver"])

PARSERS = {
    WebhookPlatform.KIWIFY: parse_kiwify_webhook,
    WebhookPlatform.PAYT: parse_payt_webhook,
    WebhookPlatform.API: parse_api_webhook,
}

MAX_BODY_BYTES = 1024 * 1024  # 1 MB — nenhum webhook de venda chega perto disso

# Duas entregas simultâneas do mesmo pedido (retry da plataforma) podem colidir
# nas chaves únicas (transactions.external_id, customers.email). Na nova tentativa
# a linha já existe e o processamento segue pelo caminho de "atualizar".
MAX_PROCESS_ATTEMPTS = 3


@router.post("/{platform}/{slug}")
async def receive_webhook(platform: str, slug: str, request: Request):
    """
    Endpoint público que recebe os POSTs das plataformas de pagamento.
    Não requer autenticação — as plataformas enviam direto.
    URL: POST /api/webhook/kiwify/{slug} | /api/webhook/payt/{slug} | /api/webhook/api/{slug}

    Respostas: 200 processado/ignorado · 4xx payload recusado (não adianta reenviar)
    · 500 falha interna (a plataforma deve reenviar; o payload já ficou salvo).
    """
    try:
        platform_enum = WebhookPlatform(platform.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Plataforma '{platform}' inválida")

    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Payload grande demais")
    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload JSON inválido")

    # Banco é síncrono: roda fora do event loop para não travar as outras requisições
    event_id = await run_in_threadpool(store_webhook, platform_enum, slug, payload)
    return await run_in_threadpool(run_stored_webhook, event_id)


def store_webhook(platform_enum: WebhookPlatform, slug: str, payload) -> int:
    """Valida o endpoint e grava o payload bruto. Retorna o id do registro."""
    with SessionLocal() as db:
        endpoint = (
            db.query(WebhookEndpoint)
            .filter(
                WebhookEndpoint.slug == slug,
                WebhookEndpoint.platform == platform_enum,
            )
            .first()
        )
        if not endpoint:
            raise HTTPException(
                status_code=404,
                detail=f"Webhook endpoint '{slug}' não encontrado para '{platform_enum.value}'",
            )

        log = WebhookEvent(
            platform=platform_enum.value,
            webhook_slug=slug,
            status="received",
            payload=payload,
            attempts=0,
        )
        db.add(log)
        db.commit()
        logger.info(f"Webhook recebido: {platform_enum.value}/{slug} | Endpoint: {endpoint.name} | log #{log.id}")
        return log.id


def _finish(event_id: int, status: str, error: str | None = None, external_id: str | None = None):
    with SessionLocal() as db:
        log = db.get(WebhookEvent, event_id)
        log.status = status
        log.error = error
        log.attempts = (log.attempts or 0) + 1
        if external_id:
            log.external_id = external_id[:255]
        if status in ("processed", "ignored"):
            log.processed_at = now_sp()
        db.commit()


def run_stored_webhook(event_id: int) -> dict:
    """Parseia e processa um webhook já gravado. Usado no recebimento e no reprocessamento."""
    with SessionLocal() as db:
        log = db.get(WebhookEvent, event_id)
        if not log:
            raise HTTPException(status_code=404, detail="Evento não encontrado")
        platform_enum = WebhookPlatform(log.platform)
        slug = log.webhook_slug
        payload = log.payload

    parser = PARSERS[platform_enum]
    event = parser(payload) if isinstance(payload, dict) else None
    external_id = (event.external_id or "").strip() if event else ""
    if not event or not external_id or external_id.lower() == "none":
        msg = "Payload sem os campos obrigatórios (external_id, status, customer_email...)"
        _finish(event_id, "rejected", msg)
        raise HTTPException(status_code=422, detail=msg)
    event.external_id = external_id

    # Ignorar emails de teste das plataformas (PayT: yoda@testsuser.com, Kiwify: johndoe@example.com)
    if is_test_email(event.customer_email):
        logger.info(f"Webhook ignorado: email de teste ({event.customer_email})")
        _finish(event_id, "ignored", "email de teste", external_id)
        return {"status": "ok", "message": "Webhook de teste ignorado"}

    # Injetar o slug do endpoint para identificar a conta de origem
    event.webhook_slug = slug

    last_error = None
    for attempt in range(1, MAX_PROCESS_ATTEMPTS + 1):
        with SessionLocal() as db:
            try:
                process_webhook_event(db, event.model_copy(deep=True))
                last_error = None
                break
            except IntegrityError as e:
                db.rollback()
                last_error = e
                logger.warning(f"Conflito ao gravar {external_id} (tentativa {attempt}): {e.orig}")
            except Exception as e:
                db.rollback()
                last_error = e
                logger.error(f"Erro ao processar webhook #{event_id} ({external_id}): {e}", exc_info=True)
                break

    if last_error is not None:
        _finish(event_id, "failed", f"{type(last_error).__name__}: {last_error}"[:2000], external_id)
        raise HTTPException(status_code=500, detail="Falha ao processar; o evento foi salvo para reprocessar")

    _finish(event_id, "processed", None, external_id)
    return {"status": "ok", "message": "Webhook processado com sucesso"}
