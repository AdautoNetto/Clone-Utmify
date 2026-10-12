"""
Preparação do banco no boot e criação do compartimento (schema) de cada conta.

- Tabelas globais (schema public): accounts, admins, webhook_routes.
- Tabelas de negócio: uma cópia por conta, no schema conta_<id>.
- Instalação antiga (conta única, tudo no public): as tabelas são MOVIDAS para
  o schema da primeira conta (nada é apagado nem copiado).
"""
import logging
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.engine import Connection

from database.core.connection import Base, engine
from database.core.migrate import run_enum_migrations
from database.core.migrate_sql import run_sql_migrations
from database.core.tenancy import is_valid_schema, schema_for
import database.models  # noqa: F401  (registra todos os modelos no Base)

logger = logging.getLogger(__name__)

_GLOBAL_TABLE_NAMES = {"accounts", "admins", "webhook_routes"}
_GLOBAL_ENUM_TYPES = {"userrole"}


def _global_tables():
    return [t for t in Base.metadata.sorted_tables if t.schema == "public"]


def _tenant_tables():
    return [t for t in Base.metadata.sorted_tables if t.schema is None]


class SchemaAlreadyExists(RuntimeError):
    """Sobrou um compartimento com o número da conta nova (ex.: depois de restaurar backup)."""


def provision_schema(conn: Connection, schema: str, new_account: bool = False) -> None:
    """
    Cria (ou atualiza) as tabelas de uma conta. Roda dentro da transação de
    `conn`: ou a conta fica completa, ou não fica nada. Pode rodar várias vezes.

    new_account=True (cadastro): o schema NÃO pode existir. Uma conta nova nunca
    herda um compartimento que já tinha dados de outra pessoa.
    """
    if not is_valid_schema(schema) or schema == "public":
        raise ValueError(f"schema inválido: {schema!r}")
    if new_account:
        exists = conn.execute(
            text("SELECT 1 FROM pg_namespace WHERE nspname = :s"), {"s": schema}
        ).first()
        if exists:
            raise SchemaAlreadyExists(schema)
    conn.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    # Só o schema da conta visível: o "já existe?" do create_all olha só para ele
    conn.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
    Base.metadata.create_all(bind=conn, tables=_tenant_tables())
    run_sql_migrations(conn)


def _legacy_tables(conn: Connection) -> list[str]:
    rows = conn.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
    )).scalars().all()
    return sorted(t for t in rows if t not in _GLOBAL_TABLE_NAMES)


def _move_legacy_to_schema(conn: Connection, legacy: list[str]) -> None:
    """Instalação de conta única → vira a conta nº 1 (ou vai para 'legado' se não havia dono)."""
    orphans = conn.execute(text(
        "SELECT id, name FROM public.admins WHERE account_id IS NULL "
        "ORDER BY (role::text = 'owner') DESC, id"
    )).fetchall()

    account_id = None
    if orphans:
        account_id = conn.execute(
            text("INSERT INTO public.accounts (name) VALUES (:n) RETURNING id"),
            {"n": orphans[0].name},
        ).scalar_one()
        conn.execute(
            text("UPDATE public.admins SET account_id = :a WHERE account_id IS NULL"),
            {"a": account_id},
        )
        target = schema_for(account_id)
    else:
        target = "legado"

    exists = conn.execute(
        text("SELECT 1 FROM pg_namespace WHERE nspname = :s"), {"s": target}
    ).first()
    if exists:
        target = f"legado_{datetime.now():%Y%m%d%H%M%S}"
    conn.exec_driver_sql(f'CREATE SCHEMA "{target}"')

    for table in legacy:
        conn.exec_driver_sql(f'ALTER TABLE public."{table}" SET SCHEMA "{target}"')

    enum_types = conn.execute(text(
        "SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace "
        "WHERE n.nspname = 'public' AND t.typtype = 'e'"
    )).scalars().all()
    for type_name in enum_types:
        if type_name not in _GLOBAL_ENUM_TYPES:
            conn.exec_driver_sql(f'ALTER TYPE public."{type_name}" SET SCHEMA "{target}"')

    if account_id is not None and "webhook_endpoints" in legacy:
        conn.exec_driver_sql(
            f'INSERT INTO public.webhook_routes (slug, account_id) '
            f'SELECT slug, {int(account_id)} FROM "{target}".webhook_endpoints '
            f'ON CONFLICT (slug) DO NOTHING'
        )
    logger.warning(
        f"Instalação de conta única convertida: {len(legacy)} tabelas movidas de 'public' para '{target}'"
    )


def bootstrap_database() -> None:
    """Chamado uma vez no boot do app."""
    with engine.connect() as conn:
        has_legacy = bool(_legacy_tables(conn))
    if has_legacy:
        # Ajustes de ENUM da versão de conta única (só fazem sentido no public)
        run_enum_migrations(engine)

    with engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL search_path TO public")
        Base.metadata.create_all(bind=conn, tables=_global_tables())
        conn.exec_driver_sql(
            "ALTER TABLE public.admins ADD COLUMN IF NOT EXISTS account_id INTEGER "
            "REFERENCES public.accounts(id)"
        )
        legacy = _legacy_tables(conn)
        if legacy:
            _move_legacy_to_schema(conn, legacy)
        account_ids = conn.execute(text("SELECT id FROM public.accounts ORDER BY id")).scalars().all()

    for account_id in account_ids:
        with engine.begin() as conn:
            provision_schema(conn, schema_for(account_id))
    logger.info(f"Banco pronto: {len(account_ids)} conta(s)")
