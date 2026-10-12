"""
Separação por conta (multi-conta).

Cada conta tem um "compartimento" próprio no Postgres (um schema: conta_1,
conta_2, ...) com todas as tabelas de negócio (vendas, clientes, produtos,
integrações...). As tabelas globais ficam no schema "public": accounts, admins
e webhook_routes.

Toda sessão do banco aponta o search_path só para o schema da conta atual
(ver database/core/connection.py). Sem conta definida, aponta para um schema
que não existe: qualquer consulta a dado de negócio falha em vez de vazar.
"""
import re
from contextlib import contextmanager
from contextvars import ContextVar

_current_account: ContextVar[int | None] = ContextVar("current_account", default=None)

# Schema inexistente de propósito: sem conta, nenhuma tabela de negócio é visível
NO_TENANT_SCHEMA = "_sem_conta"
_SCHEMA_RE = re.compile(r"^(conta_[0-9]{1,12}|legado(_[0-9]{1,14})?|public|_sem_conta)$")


def schema_for(account_id: int) -> str:
    return f"conta_{int(account_id)}"


def is_valid_schema(schema: str) -> bool:
    return bool(_SCHEMA_RE.match(schema or ""))


def current_account_id() -> int | None:
    return _current_account.get()


def current_schema() -> str | None:
    account_id = _current_account.get()
    return schema_for(account_id) if account_id is not None else None


def set_current_account(account_id: int | None):
    """Define a conta da requisição atual. Devolve o token para desfazer."""
    return _current_account.set(int(account_id) if account_id is not None else None)


def reset_current_account(token) -> None:
    _current_account.reset(token)


@contextmanager
def account_context(account_id: int | None):
    token = set_current_account(account_id)
    try:
        yield
    finally:
        reset_current_account(token)
