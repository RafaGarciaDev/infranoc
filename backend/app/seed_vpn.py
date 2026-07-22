"""Seed de usuarios VPN e sessoes simuladas (Fase 9i).

Rodar:  uv run python -m app.seed_vpn
"""
import asyncio
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.domain.models import Tenant, VpnSession, VpnUser

TENANT_SLUG = "valeverde"

_USERS = [
    ("Ricardo Andrade Nunes", "ricardo.andrade@infranoc.lab", "ricardo.andrade", True),
    ("Fernanda Costa Almeida", "fernanda.costa@infranoc.lab", "fernanda.costa", True),
    ("Marcelo Vieira Santos", "marcelo.vieira@infranoc.lab", "marcelo.vieira", True),
    ("Camila Rocha Pereira", "camila.rocha@infranoc.lab", "camila.rocha", True),
    ("Diego Nunes Barbosa", "diego.nunes@infranoc.lab", "diego.nunes", True),
    ("Ex-Funcionario Teste", "ex.funcionario@infranoc.lab", None, False),
]


def _fake_public_key() -> str:
    return secrets.token_urlsafe(32)[:43] + "="


async def seed_vpn():
    async with SessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        ).scalar_one_or_none()
        if not tenant:
            print("[ERRO] Tenant valeverde nao existe. Rode 'uv run python -m app.seed' primeiro.")
            return

        existing = (
            await session.execute(select(VpnUser).where(VpnUser.tenant_id == tenant.id))
        ).scalars().all()
        if existing:
            print(f"[=] Ja existem {len(existing)} usuarios VPN. Nada a fazer.")
            return

        agora = datetime.now(timezone.utc)
        for i, (name, email, ad_sam, active) in enumerate(_USERS, start=2):
            user = VpnUser(
                tenant_id=tenant.id,
                name=name,
                email=email,
                ad_sam=ad_sam,
                public_key=_fake_public_key(),
                internal_ip=f"10.10.0.{i}",
                active=active,
                expires_at=agora + timedelta(days=90) if active else agora - timedelta(days=5),
            )
            session.add(user)
            await session.flush()

            if active:
                if name == "Diego Nunes Barbosa":
                    last_handshake = agora - timedelta(hours=6)
                else:
                    last_handshake = agora - timedelta(minutes=int(2 + i))
                session.add(
                    VpnSession(
                        vpn_user_id=user.id,
                        endpoint_publico=f"189.45.{i}.{i * 3}:51820",
                        connected_at=agora - timedelta(hours=3),
                        last_handshake=last_handshake,
                        bytes_rx=1_000_000 * (i + 3),
                        bytes_tx=500_000 * (i + 2),
                    )
                )

        await session.commit()
        print(f"[+] {len(_USERS)} usuarios VPN criados, com sessoes simuladas.")


if __name__ == "__main__":
    asyncio.run(seed_vpn())
