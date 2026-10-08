import os
import logging
import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt

logger = logging.getLogger(__name__)

# Chave pública que vinha como padrão no código/compose. Com ela qualquer pessoa
# consegue forjar um login válido, então nunca é aceita.
_INSECURE_KEYS = {"", "convergeai-secret-key-change-in-production", "sua_chave_secreta_aqui"}

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if SECRET_KEY in _INSECURE_KEYS or len(SECRET_KEY) < 32:
    logger.warning(
        "SECRET_KEY ausente, padrão ou curta (<32). Usando uma chave aleatória temporária: "
        "os logins expiram a cada reinício. Defina SECRET_KEY no ambiente."
    )
    SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None
