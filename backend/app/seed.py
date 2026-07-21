"""Seed inicial do InfraNOC.

Cria (de forma idempotente):
  - Tenant "Laticínios Vale Verde S/A" (slug: valeverde)
  - Permissões do MVP (cmdb, ad, obs, alerts, audit)
  - Papel "Admin" com todas as permissões
  - Usuário admin@valeverde.com

Rodar:  uv run python -m app.seed
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.domain.models import Permission, Role, Tenant, User

TENANT_NAME = "Laticínios Vale Verde S/A"
TENANT_SLUG = "valeverde"

ADMIN_EMAIL = "admin@valeverde.com"
ADMIN_PASSWORD = "admin"  # troque depois; suficiente para o lab/demo
ADMIN_NAME = "Administrador InfraNOC"

PERMISSIONS = [
    ("cmdb.read", "Ler ativos do CMDB"),
    ("cmdb.write", "Criar/editar ativos"),
    ("cmdb.admin", "Administrar o CMDB"),
    ("ad.read", "Ler usuários do Active Directory"),
    ("ad.write", "Criar/editar/mover usuários e grupos do AD"),
    ("ad.reset-password", "Resetar senha de usuários do AD"),
    ("obs.read", "Ler métricas e dashboards de observabilidade"),
    ("alerts.read", "Ler alertas"),
    ("alerts.ack", "Reconhecer (acknowledge) alertas"),
    ("audit.read", "Ler trilha de auditoria"),
    ("ai.chat", "Usar o assistente de IA"),
    ("integrations.read", "Ler configuracoes de integracao"),
    ("integrations.write", "Editar configuracoes de integracao"),
    ("tickets.read", "Ler chamados (ITSM)"),
    ("wiki.read", "Ler paginas da base de conhecimento"),
    ("wiki.write", "Criar/editar paginas da base de conhecimento"),
    ("ad.ou.manage", "Criar/renomear/mover/excluir OUs do Active Directory"),
    ("ad.group.manage", "Criar/editar/excluir grupos do Active Directory"),
    ("linux.read", "Ler status de servidores Linux (systemd, disco, usuarios)"),
    ("linux.exec", "Executar acoes em servidores Linux (start/stop/restart de servicos)"),
    ("toolkit.exec", "Executar ferramentas de diagnostico (port-check, ss, etc.)"),
    ("backup.read", "Ver painel de backup (jobs, restore points, KPIs)"),
]


async def seed():
    async with SessionLocal() as session:
        # --- Tenant ---
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        ).scalar_one_or_none()
        if not tenant:
            tenant = Tenant(name=TENANT_NAME, slug=TENANT_SLUG, active=True)
            session.add(tenant)
            await session.flush()
            print(f"[+] Tenant criado: {TENANT_NAME}")
        else:
            print(f"[=] Tenant já existe: {TENANT_NAME}")

        # --- Permissões ---
        existing_keys = set(
            (await session.execute(select(Permission.key))).scalars().all()
        )
        perms: list[Permission] = []
        for key, desc in PERMISSIONS:
            if key not in existing_keys:
                p = Permission(key=key, description=desc)
                session.add(p)
                perms.append(p)
                print(f"[+] Permissão criada: {key}")
        await session.flush()

        # recarrega todas as permissões (novas + já existentes)
        all_perms = (await session.execute(select(Permission))).scalars().all()

        # --- Papel Admin (com todas as permissões) ---
        role = (
            await session.execute(
                select(Role)
                .where(Role.tenant_id == tenant.id, Role.name == "Admin")
                .options(selectinload(Role.permissions))
            )
        ).scalar_one_or_none()
        if not role:
            role = Role(tenant_id=tenant.id, name="Admin")
            role.permissions = list(all_perms)
            session.add(role)
            print("[+] Papel 'Admin' criado com todas as permissões")
        else:
            role.permissions = list(all_perms)  # garante que tem todas
            print("[=] Papel 'Admin' já existia (permissões sincronizadas)")
        await session.flush()

        # --- Usuário admin ---
        user = (
            await session.execute(select(User).where(User.email == ADMIN_EMAIL))
        ).scalar_one_or_none()
        if not user:
            user = User(
                tenant_id=tenant.id,
                email=ADMIN_EMAIL,
                password_hash=hash_password(ADMIN_PASSWORD),
                display_name=ADMIN_NAME,
                active=True,
            )
            user.roles = [role]
            session.add(user)
            print(f"[+] Usuário criado: {ADMIN_EMAIL} (senha: {ADMIN_PASSWORD})")
        else:
            print(f"[=] Usuário já existe: {ADMIN_EMAIL}")

        await session.commit()
        print("\n✅ Seed concluído.")


if __name__ == "__main__":
    asyncio.run(seed())
