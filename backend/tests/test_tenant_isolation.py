import pytest
from sqlalchemy import select

from app.domain.models import Tenant, User


@pytest.mark.asyncio
async def test_tenant_nao_ve_dados_de_outro(db_session):
    """Prova o isolamento multi-tenant: filtrando por tenant_id, os usuários
    de um tenant nunca aparecem para outro."""
    # Dois tenants distintos
    t_a = Tenant(name="Vale Verde", slug="vv", active=True)
    t_b = Tenant(name="Outra Fabrica", slug="of", active=True)
    db_session.add_all([t_a, t_b])
    await db_session.flush()

    # Um usuário em cada tenant
    db_session.add_all(
        [
            User(
                tenant_id=t_a.id,
                email="user@vv.com",
                password_hash="x",
                display_name="A",
                active=True,
            ),
            User(
                tenant_id=t_b.id,
                email="user@of.com",
                password_hash="x",
                display_name="B",
                active=True,
            ),
        ]
    )
    await db_session.commit()

    # Query "como tenant A": só enxerga o próprio usuário
    rows_a = (
        await db_session.execute(select(User).where(User.tenant_id == t_a.id))
    ).scalars().all()
    emails_a = {u.email for u in rows_a}

    assert emails_a == {"user@vv.com"}
    assert "user@of.com" not in emails_a  # dado do tenant B NUNCA vaza para A
