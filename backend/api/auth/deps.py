from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database.core.connection import get_db
from api.auth.token import verify_token
from database.models.admin import Admin, UserRole

security = HTTPBearer()

_READ_METHODS = {"GET", "HEAD", "OPTIONS"}

# Únicas ações de escrita liberadas para o papel "viewer": a própria conta e
# perguntar à IA (as ferramentas da IA só leem; ações da IA em campanhas usam
# /api/campaigns/ai-action, que continua bloqueado).
_VIEWER_WRITE_ALLOWED = {
    ("PUT", "/api/profile"),
    ("PUT", "/api/profile/password"),
    ("POST", "/api/gemini/chat"),
    ("POST", "/api/gemini/daily-report"),
}


def _block_viewer_writes(request: Request, admin: Admin) -> None:
    """
    Viewer é somente leitura. A regra fica aqui (e não em cada rota) para que
    toda rota de escrita nova já nasça protegida.
    """
    if admin.role != UserRole.viewer or request.method in _READ_METHODS:
        return
    path = request.url.path.rstrip("/") or "/"
    if (request.method, path) in _VIEWER_WRITE_ALLOWED:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Seu usuário é só de visualização: não pode alterar dados",
    )


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Admin:
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin_id = payload.get("sub")
    if admin_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _block_viewer_writes(request, admin)
    return admin


def require_role(*roles: UserRole):
    """Dependency that checks if the current user has one of the required roles."""
    def _check(current_user: Admin = Depends(get_current_user)) -> Admin:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar este recurso",
            )
        return current_user
    return _check
