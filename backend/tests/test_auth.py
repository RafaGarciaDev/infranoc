import pytest

from app.application import auth_service
from app.core.security import hash_password
from app.domain.models import Permission, Role, Tenant, User


async def _seed_min(session):
    tenant = Tenant(name="Vale Verde", slug="vv", active=True)
    session.add(tenant)
    await session.flush()

    perm = Permission(key="cmdb.read", description="ler")
    session.add(perm)
    await session.flush()

    role = Role(tenant_id=tenant.id, name="Admin")
    role.permissions = [perm]
    session.add(role)
    await session.flush()

    user = User(
        tenant_id=tenant.id,
        email="admin@vv.com",
        password_hash=hash_password("segredo"),
        display_name="Admin",
        active=True,
    )
    user.roles = [role]
    session.add(user)
    await session.commit()
    return tenant


@pytest.mark.asyncio
async def test_login_valido_emite_token(db_session):
    await _seed_min(db_session)
    result = await auth_service.login(db_session, "admin@vv.com", "segredo")
    assert result is not None
    assert result["access_token"]
    assert result["refresh_token"]
    assert "cmdb.read" in result["permissions"]


@pytest.mark.asyncio
async def test_login_senha_errada_falha(db_session):
    await _seed_min(db_session)
    result = await auth_service.login(db_session, "admin@vv.com", "errada")
    assert result is None
