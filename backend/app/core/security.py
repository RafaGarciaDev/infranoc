from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.core.config import settings


# --- Hash de senha (bcrypt direto) ---
# Nota: usamos a lib `bcrypt` diretamente em vez de passlib. O passlib 1.7.4
# (sem manutenção) quebra com bcrypt >= 4.1/5.0 ao tentar ler um atributo de
# versão removido. Usar bcrypt direto é mais moderno e mantém a mesma interface.

def hash_password(p: str) -> str:
    hashed = bcrypt.hashpw(p.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode("utf-8"), h.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JWT (python-jose) ---
def create_access_token(sub: str, tenant_id: str, perms: list[str]) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_expire_min)
    payload = {"sub": sub, "tenant_id": tenant_id, "perm": perms, "exp": exp, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret, settings.jwt_algorithm)


def create_refresh_token(sub: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=settings.refresh_expire_days)
    return jwt.encode(
        {"sub": sub, "exp": exp, "type": "refresh"}, settings.jwt_secret, settings.jwt_algorithm
    )


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
