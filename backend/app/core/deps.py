from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.db import current_tenant, current_user_email
from app.core.security import decode_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_claims(token: str = Depends(oauth2)) -> dict:
    try:
        claims = decode_token(token)
        if claims.get("type") != "access":
            raise ValueError()
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido")
    current_tenant.set(claims["tenant_id"])
    current_user_email.set(claims["sub"])
    return claims


def require(*perms: str):
    """Dependency de RBAC: exige que o token tenha todas as permissoes."""

    async def _check(claims: dict = Depends(get_current_claims)):
        have = set(claims.get("perm", []))
        if not set(perms).issubset(have):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissao")
        return claims

    return _check
