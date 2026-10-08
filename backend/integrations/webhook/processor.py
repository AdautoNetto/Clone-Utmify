import logging
from sqlalchemy import text
from sqlalchemy.orm import Session

from integrations.webhook.schemas import StandardizedWebhookEvent
from integrations.webhook.auto_product import ensure_product_from_webhook
from database.models.customer import Customer
from database.models.transaction import Transaction, TransactionStatus
from database.models.customer_product import CustomerProduct
from database.core.timezone import now_sp
from integrations.webhook.recovery_helper import (
    create_recovery_if_pending,
    mark_recovery_as_recovered,
)

logger = logging.getLogger(__name__)


def get_saopaulo_time():
    """Helper para pegar o tempo exato de São Paulo."""
    return now_sp()


_WEBHOOK_LOCK_KEY = 74_201_605  # número arbitrário, só identifica a trava

# Ordem do ciclo de vida de uma venda. Só se avança, nunca se volta.
_STATUS_RANK = {
    TransactionStatus.PENDING: 0,
    TransactionStatus.TRIAL: 1,
    TransactionStatus.APPROVED: 2,
    TransactionStatus.REFUNDED: 3,
    TransactionStatus.CHARGEBACK: 3,
}

_FILLABLE_FIELDS = (
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "src", "checkout_url", "webhook_slug", "product_name",
)


def _grant_product(db: Session, customer_id: int, product_id: int):
    """Libera o produto para o cliente (junction CustomerProduct), sem duplicar."""
    already_has = db.query(CustomerProduct).filter(
        CustomerProduct.customer_id == customer_id,
        CustomerProduct.product_id == product_id,
    ).first()
    if not already_has:
        db.add(CustomerProduct(customer_id=customer_id, product_id=product_id))


def _fill_missing_fields(tx: Transaction, event: StandardizedWebhookEvent):
    """Completa campos vazios da transação com o que chegou no evento mais novo."""
    for field in _FILLABLE_FIELDS:
        value = getattr(event, field, None)
        if value and not getattr(tx, field):
            setattr(tx, field, value)
    if event.order_bumps and not tx.order_bumps:
        tx.order_bumps = event.order_bumps


def process_webhook_event(db: Session, event: StandardizedWebhookEvent):
    """
    Processa um evento padronizado de webhook, atualizando as tabelas:
    1. Customer (cria ou atualiza saldos se for compra aprovada)
    2. Transaction (registra a transação com suas utms)
    3. CustomerProduct (libera o produto para o usuário se não tinha e se for aprovada)
    4. Recovery (cria registro de recuperação se for pendente)
    """
    logger.info(f"Processando webhook event: {event.external_id} | Status: {event.status}")

    # Um webhook por vez (trava liberada no commit/rollback). Sem isso, vendas
    # simultâneas do mesmo cliente perdem soma em total_spent/total_orders, e o
    # mesmo produto novo pode ser criado duas vezes. Cada evento leva milissegundos.
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _WEBHOOK_LOCK_KEY})

    # -------------------------------------------------------------
    # 1. PROCESSAMENTO DO CUSTOMER
    # -------------------------------------------------------------
    customer = db.query(Customer).filter(Customer.email == event.customer_email).first()
    
    if not customer:
        customer = Customer(
            external_id=event.customer_external_id,
            email=event.customer_email,
            name=event.customer_name,
            cpf=event.customer_cpf,
            phone=event.customer_phone,
            total_spent=0.0,
            total_orders=0
        )
        db.add(customer)
        db.flush()
    else:
        if event.customer_external_id and not customer.external_id:
            customer.external_id = event.customer_external_id
        if event.customer_name and not customer.name:
            customer.name = event.customer_name
        if event.customer_cpf and not customer.cpf:
            customer.cpf = event.customer_cpf
        if event.customer_phone and not customer.phone:
            customer.phone = event.customer_phone

    # -------------------------------------------------------------
    # 2. SE A TRANSAÇÃO JÁ EXISTIR
    # -------------------------------------------------------------
    existing_tx = db.query(Transaction).filter(Transaction.external_id == event.external_id).first()
    
    if existing_tx:
        logger.info(f"Transação {event.external_id} já existia. Status: {existing_tx.status} -> {event.status}")
        _fill_missing_fields(existing_tx, event)

        # Webhooks chegam fora de ordem (retries, filas). Um evento "atrasado"
        # nunca pode rebaixar o status: approved → pending faria a venda sumir
        # das métricas; refunded → approved ressuscitaria uma venda devolvida.
        if _STATUS_RANK[event.status] <= _STATUS_RANK[existing_tx.status]:
            if event.status != existing_tx.status:
                logger.warning(
                    f"Ignorando mudança de status fora de ordem em {event.external_id}: "
                    f"{existing_tx.status} -> {event.status}"
                )
            db.commit()
            return existing_tx

        is_newly_approved = event.status == TransactionStatus.APPROVED
        is_newly_refunded = existing_tx.status == TransactionStatus.APPROVED and event.status in [TransactionStatus.REFUNDED, TransactionStatus.CHARGEBACK]

        # O pendente às vezes chega sem valor (ex.: abandono); o aprovado traz o valor real
        if is_newly_approved and event.amount > 0:
            existing_tx.amount = event.amount

        existing_tx.status = event.status

        if is_newly_approved:
            customer.total_spent += existing_tx.amount
            customer.total_orders += 1
            customer.last_purchase_at = get_saopaulo_time()
            if not customer.first_purchase_at:
                customer.first_purchase_at = customer.last_purchase_at
            mark_recovery_as_recovered(db, event.customer_email, event.product_name, event.src)

            if not existing_tx.product_id:
                product = ensure_product_from_webhook(db, event)
                if product:
                    existing_tx.product_id = product.id
            if existing_tx.product_id:
                _grant_product(db, customer.id, existing_tx.product_id)
                
        elif is_newly_refunded:
            customer.total_spent -= existing_tx.amount
            customer.total_orders -= 1
            if customer.total_orders < 0:
                customer.total_orders = 0
            if customer.total_spent < 0:
                customer.total_spent = 0.0

        create_recovery_if_pending(db, event, customer)
        db.commit()
        return existing_tx
    
    # -------------------------------------------------------------
    # 3. TRANSAÇÃO NOVA
    # -------------------------------------------------------------
    if event.status == TransactionStatus.APPROVED:
        customer.total_spent += event.amount
        customer.total_orders += 1
        customer.last_purchase_at = get_saopaulo_time()
        if not customer.first_purchase_at:
            customer.first_purchase_at = customer.last_purchase_at

    # Auto-criação de produto (se não existir, cria com checkout + alias)
    product = ensure_product_from_webhook(db, event)
    product_id_to_save = product.id if product else None
    
    amount_to_save = event.amount
    # Se for uma nova transação de chargeback/reembolso recebida direto (ex: reenvio webhooks de histórico)
    # e chegar aqui com 0, tentamos copiar da possível venda original usando email e nome do produto (já que external_id falhou).
    if event.status in [TransactionStatus.REFUNDED, TransactionStatus.CHARGEBACK] and amount_to_save == 0.0:
        original_tx = db.query(Transaction).filter(
            Transaction.customer_email == event.customer_email,
            Transaction.product_name == event.product_name,
            Transaction.status == TransactionStatus.APPROVED
        ).order_by(Transaction.id.desc()).first()
        
        if original_tx:
            amount_to_save = original_tx.amount
    
    new_tx = Transaction(
        external_id=event.external_id,
        platform=event.platform,
        status=event.status,
        amount=amount_to_save,
        customer_id=customer.id,
        product_id=product_id_to_save,
        product_name=event.product_name,
        customer_email=customer.email,
        utm_source=event.utm_source,
        utm_medium=event.utm_medium,
        utm_campaign=event.utm_campaign,
        utm_content=event.utm_content,
        utm_term=event.utm_term,
        src=event.src,
        webhook_slug=event.webhook_slug,
        checkout_url=event.checkout_url,
        order_bumps=event.order_bumps
    )
    db.add(new_tx)
    
    # -------------------------------------------------------------
    # 4. LIBERAR ACESSO AO PRODUTO (Junction CustomerProduct)
    # -------------------------------------------------------------
    if product and event.status == TransactionStatus.APPROVED:
        _grant_product(db, customer.id, product.id)

    # -------------------------------------------------------------
    # 5. CRIAR RECOVERY SE PENDENTE
    # -------------------------------------------------------------
    create_recovery_if_pending(db, event, customer)
    
    db.commit()
    logger.info(f"Webhook processado com sucesso. Transação: {new_tx.id}")
    return new_tx
