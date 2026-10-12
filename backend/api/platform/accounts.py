"""
Tela "Contas": só para quem administra o SISTEMA (não confundir com o dono de
uma conta). É o único lugar que olha para mais de uma conta ao mesmo tempo —
por isso tudo aqui exige require_platform_admin e usa o nome completo do
schema de cada conta.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.auth.deps import require_platform_admin
from api.auth.password_reset import ADMIN_LINK_HOURS, create_reset_token
from api.platform.settings_store import load_email_config, save_settings
from database.core.connection import get_db
from database.core.tenancy import schema_for
from database.models.account import Account, WebhookRoute
from database.models.admin import Admin, UserRole
from integrations.email.smtp import describe_error, send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/platform", tags=["platform"])


class BlockRequest(BaseModel):
    blocked: bool


class DeleteRequest(BaseModel):
    confirm_email: str


class EmailSettingsRequest(BaseModel):
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""  # vazio = manter a que já está salva
    smtp_from_name: str = ""
    public_url: str = ""


def _owner_of(db: Session, account_id: int) -> Admin | None:
    return (
        db.query(Admin)
        .filter(Admin.account_id == account_id, Admin.role == UserRole.owner, Admin.email.isnot(None))
        .order_by(Admin.id)
        .first()
    )


def _get_account(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    return account


@router.get("/accounts")
def list_accounts(
    db: Session = Depends(get_db),
    current_user: Admin = Depends(require_platform_admin),
):
    accounts = db.query(Account).order_by(Account.id).all()
    users = db.query(Admin).order_by(Admin.id).all()
    schemas = set(db.execute(text(
        "SELECT nspname FROM pg_namespace WHERE nspname LIKE 'conta\\_%'"
    )).scalars())

    result = []
    for account in accounts:
        members = [u for u in users if u.account_id == account.id]
        owner = next((u for u in members if u.role == UserRole.owner and u.email), None)
        sales, last_sale = 0, None
        schema = schema_for(account.id)
        if schema in schemas:
            sales, last_sale = db.execute(text(
                f'SELECT count(*), max(created_at) FROM "{schema}".transactions'
            )).one()
        result.append({
            "id": account.id,
            "name": account.name,
            "owner_email": owner.email if owner else None,
            "users": len([u for u in members if u.email]),
            "sales": sales,
            "last_sale_at": last_sale.isoformat() if last_sale else None,
            "created_at": account.created_at.isoformat() if account.created_at else None,
            "blocked": bool(account.blocked),
            "is_mine": account.id == current_user.account_id,
        })
    return result


@router.put("/accounts/{account_id}/block")
def block_account(
    account_id: int, data: BlockRequest,
    db: Session = Depends(get_db),
    current_user: Admin = Depends(require_platform_admin),
):
    """Bloqueada: ninguém da conta entra. As vendas dela continuam sendo recebidas e guardadas."""
    account = _get_account(db, account_id)
    if account.id == current_user.account_id:
        raise HTTPException(status_code=400, detail="Você não pode bloquear a sua própria conta")
    account.blocked = data.blocked
    db.commit()
    logger.warning(f"Conta {account.id} {'bloqueada' if data.blocked else 'desbloqueada'} por {current_user.id}")
    return {"id": account.id, "blocked": account.blocked}


@router.post("/accounts/{account_id}/delete")
def delete_account(
    account_id: int, data: DeleteRequest,
    db: Session = Depends(get_db),
    current_user: Admin = Depends(require_platform_admin),
):
    """
    Apaga a conta INTEIRA (logins e todos os dados dela). Não tem volta pelo
    painel — só restaurando um backup. Exige digitar o e-mail do dono.
    """
    account = _get_account(db, account_id)
    if account.id == current_user.account_id:
        raise HTTPException(status_code=400, detail="Você não pode excluir a sua própria conta")
    owner = _owner_of(db, account.id)
    expected = (owner.email if owner else account.name).strip().lower()
    if data.confirm_email.strip().lower() != expected:
        raise HTTPException(status_code=400, detail="O e-mail digitado não confere com o do dono da conta")

    schema = schema_for(account.id)
    db.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    db.query(WebhookRoute).filter(WebhookRoute.account_id == account.id).delete()
    db.query(Admin).filter(Admin.account_id == account.id).delete()
    db.delete(account)
    db.commit()
    logger.warning(f"Conta {account_id} ({expected}) EXCLUÍDA por {current_user.id}")
    return {"message": "Conta excluída"}


@router.post("/accounts/{account_id}/reset-link")
def create_reset_link(
    account_id: int,
    db: Session = Depends(get_db),
    _: Admin = Depends(require_platform_admin),
):
    """Gera um link de senha nova para o dono da conta (para mandar por WhatsApp, por exemplo)."""
    account = _get_account(db, account_id)
    owner = _owner_of(db, account.id)
    if not owner:
        raise HTTPException(status_code=400, detail="Esta conta não tem dono com e-mail")
    token = create_reset_token(db, owner, ADMIN_LINK_HOURS)
    db.commit()
    return {"path": f"/reset?token={token}", "email": owner.email, "hours": ADMIN_LINK_HOURS}


# ── Envio de e-mail (para o "Esqueci minha senha" chegar sozinho) ──────────

def _email_settings_view(cfg) -> dict:
    return {
        "smtp_host": cfg.smtp_host,
        "smtp_port": cfg.smtp_port,
        "smtp_user": cfg.smtp_user,
        "smtp_from_name": cfg.smtp_from_name,
        "public_url": cfg.public_url,
        "has_password": bool(cfg.smtp_password),  # a senha em si nunca sai do servidor
        "configured": cfg.configured,
    }


@router.get("/email-settings")
def get_email_settings(
    db: Session = Depends(get_db),
    _: Admin = Depends(require_platform_admin),
):
    return _email_settings_view(load_email_config(db))


@router.put("/email-settings")
def update_email_settings(
    data: EmailSettingsRequest,
    db: Session = Depends(get_db),
    _: Admin = Depends(require_platform_admin),
):
    public_url = data.public_url.strip().rstrip("/")
    if public_url and not (public_url.startswith("https://") or public_url.startswith("http://localhost")):
        raise HTTPException(status_code=400, detail="O endereço do painel deve começar com https://")
    if not (1 <= data.smtp_port <= 65535):
        raise HTTPException(status_code=400, detail="Porta inválida")
    values = {
        "smtp_host": data.smtp_host.strip(),
        "smtp_port": str(data.smtp_port),
        "smtp_user": data.smtp_user.strip(),
        "smtp_from_name": data.smtp_from_name.strip()[:60],
        "public_url": public_url,
    }
    if data.smtp_password:
        values["smtp_password"] = data.smtp_password.replace(" ", "")  # senha de app do Gmail vem com espaços
    save_settings(db, values)
    db.commit()
    return _email_settings_view(load_email_config(db))


@router.post("/email-settings/test")
def test_email_settings(
    db: Session = Depends(get_db),
    current_user: Admin = Depends(require_platform_admin),
):
    cfg = load_email_config(db)
    if not cfg.configured:
        raise HTTPException(status_code=400, detail="Preencha e salve todos os campos antes de testar")
    try:
        send_email(
            cfg, current_user.email, "Teste de envio de e-mail",
            "Este é um e-mail de teste do painel. Se chegou, o envio está funcionando.\n",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=describe_error(e))
    return {"message": f"E-mail de teste enviado para {current_user.email}"}
