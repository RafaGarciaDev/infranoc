"""Seed do usuario demo (somente leitura) do InfraNOC.

Cria (de forma idempotente):
  - Papel "Demo" com permissoes de somente leitura
  - Usuario demo@valeverde.com

Rodar:  uv run python -m app.seed_demo
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.domain.models import Permission, Role, Tenant, User

TENANT_SLUG = "valeverde"

DEMO_EMAIL = "demo@valeverde.com"
DEMO_PASSWORD = "demo"
DEMO_NAME = "Visitante (Demo)"

DEMO_PERMISSIONS = [
    "cmdb.read",
    "ad.read",
    "alerts.read",
    "obs.read",
    "audit.read",
    "ai.chat",
    "tickets.read",
    "integrations.read",
]


async def seed_demo():
    async with SessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        ).scalar_one_or_none()
        if not tenant:
            print("[ERRO] Tenant valeverde nao existe. Rode 'uv run python -m app.seed' primeiro.")
            return

        all_perms = (
            await session.execute(
                select(Permission).where(Permission.key.in_(DEMO_PERMISSIONS))
            )
        ).scalars().all()
        found_keys = {p.key for p in all_perms}
        missing = set(DEMO_PERMISSIONS) - found_keys
        if missing:
            print(f"[ERRO] Permissoes faltando no banco: {missing}. Rode o seed principal primeiro.")
            return

        role = (
            await session.execute(
                select(Role)
                .where(Role.tenant_id == tenant.id, Role.name == "Demo")
                .options(selectinload(Role.permissions))
            )
        ).scalar_one_or_none()
        if not role:
            role = Role(tenant_id=tenant.id, name="Demo")
            role.permissions = list(all_perms)
            session.add(role)
            print("[+] Papel 'Demo' criado com permissoes de somente leitura")
        else:
            role.permissions = list(all_perms)
            print("[=] Papel 'Demo' ja existia (permissoes sincronizadas)")
        await session.flush()

        user = (
            await session.execute(select(User).where(User.email == DEMO_EMAIL))
        ).scalar_one_or_none()
        if not user:
            user = User(
                tenant_id=tenant.id,
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                display_name=DEMO_NAME,
                active=True,
            )
            user.roles = [role]
            session.add(user)
            print(f"[+] Usuario demo criado: {DEMO_EMAIL} (senha: {DEMO_PASSWORD})")
        else:
            user.roles = [role]
            print(f"[=] Usuario demo ja existe: {DEMO_EMAIL} (papel sincronizado)")

        await session.commit()
        print("\nSeed demo concluido.")


if __name__ == "__main__":
    asyncio.run(seed_demo())
