import os
import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/logpose"
)


def _normalize_url(url: str) -> str:
    """
    Fixa o driver psycopg2 (o único instalado). Sem isso:
    - 'postgres://' (formato do README/Heroku/Coolify) não é aceito pelo SQLAlchemy 2;
    - 'postgresql://' passa a exigir o pacote psycopg (v3) no SQLAlchemy 2.1+.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


engine = create_engine(_normalize_url(DATABASE_URL), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def wait_for_database(timeout_seconds: int = 60) -> None:
    """Espera o Postgres aceitar conexões (o container do app pode subir antes)."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as e:
            if time.monotonic() >= deadline:
                raise
            logger.warning(f"Banco ainda indisponível ({type(e).__name__}); tentando de novo em 2s")
            time.sleep(2)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
