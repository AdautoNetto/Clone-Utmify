import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.core.connection import get_db
from database.models.transaction import Transaction, TransactionStatus
from database.models.refund_reason import RefundReason
from database.models.customer import Customer
from database.models.customer_product import CustomerProduct
from api.auth.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sales", tags=["sales"])


@router.delete("/transactions/{transaction_id}", status_code=204)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Apaga uma transação e, se o customer não tiver outras transações,
    apaga o customer e seus registros de customer_product também.
    Útil para limpar dados de teste das plataformas de pagamento.
    """
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    customer_id = tx.customer_id

    # Se era venda aprovada, tirar do total do cliente (senão o "gasto total" fica inflado)
    if customer_id and tx.status == TransactionStatus.APPROVED:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if customer:
            customer.total_spent = max(0.0, (customer.total_spent or 0.0) - (tx.amount or 0.0))
            customer.total_orders = max(0, (customer.total_orders or 0) - 1)

    # O motivo de reembolso aponta para a transação (FK): apagar antes
    db.query(RefundReason).filter(
        RefundReason.transaction_id == transaction_id
    ).delete(synchronize_session=False)

    # Apagar a transação
    db.delete(tx)
    db.flush()

    # Se tinha customer vinculado, verificar se ficou órfão
    if customer_id:
        _cleanup_orphan_customer(db, customer_id)

    db.commit()
    logger.info(f"Transação {transaction_id} apagada com sucesso")


def _cleanup_orphan_customer(db: Session, customer_id: int):
    """Remove o customer e seus customer_products se não tiver mais transações."""
    remaining = db.query(Transaction).filter(
        Transaction.customer_id == customer_id
    ).count()

    if remaining == 0:
        # Apagar registros de customer_product
        db.query(CustomerProduct).filter(
            CustomerProduct.customer_id == customer_id
        ).delete(synchronize_session=False)

        # Apagar o customer
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if customer:
            db.delete(customer)
            logger.info(f"Customer órfão {customer_id} apagado")
