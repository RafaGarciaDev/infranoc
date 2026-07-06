from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token, create_refresh_token, verify_password
from app.domain.models import Role, User


async def login(session, email: str, password: str):
    # Em SQLAlchemy async não há lazy loading: precisamos pré-carregar
    # roles E as permissions de cada role antes de acessá-las.
    q = (
        select(User)
        .where(User.email == email, User.active.is_(True))
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    user = (await session.execute(q)).scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    perms = sorted({p.key for r in user.roles for p in r.permissions})
    return {
        "access_token": create_access_token(user.email, str(user.tenant_id), perms),
        "refresh_token": create_refresh_token(user.email),
        "display_name": user.display_name,
        "permissions": perms,
        "token_type": "bearer",
    }
