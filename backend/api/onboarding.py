"""Primeiros passos de uma conta nova: o que já foi feito e o que falta."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.auth.deps import get_current_user
from database.core.connection import get_db
from database.models.facebook_account import FacebookAccount
from database.models.transaction import Transaction
from database.models.webhook_endpoint import WebhookEndpoint

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/status")
def onboarding_status(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return {
        "has_endpoint": db.query(WebhookEndpoint.id).first() is not None,
        "has_sale": db.query(Transaction.id).first() is not None,
        "has_facebook": db.query(FacebookAccount.id).first() is not None,
    }
