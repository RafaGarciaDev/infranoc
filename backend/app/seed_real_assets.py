"""Seed dos 2 ativos reais do lab (DC01, MES01) no CMDB.

Historicamente estes dois nunca foram inseridos como Asset - so existem
como alvos de scrape do Prometheus (windows_exporter/node_exporter, Fase 3)
e como strings soltas em seed_backup.py/seed_security.py. Essa lacuna foi
descoberta ao implementar a Fase 9L (Console de Dispositivos), que precisa
de um asset_id real para vincular DeviceProtocolProfile.

Rodar:  uv run python -m app.seed_real_assets
"""

import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.domain.enums import AssetStatus, AssetType, Criticality, Layer
from app.domain.models import Asset, Sector, Tenant

TENANT_SLUG = "valeverde"
SECTOR_NAME = "Ti Datacenter"

REAL_ASSETS = [
    dict(
        name="PSA-TI-DC01",
        display_name="PSA-TI-DC01 (Active Directory)",
        type=AssetType.Server,
        layer=Layer.TI,
        site="PSA",
        criticality=Criticality.Critical,
        ip_address="192.168.56.10",
        hostname="PSA-TI-DC01",
        description="Windows Server 2022 - controlador de dominio real do lab (Fase 1/5).",
    ),
    dict(
        name="PSA-OT-MES01",
        display_name="PSA-OT-MES01 (MES Linux)",
        type=AssetType.Server,
        layer=Layer.OT,
        site="PSA",
        criticality=Criticality.High,
        ip_address="192.168.56.30",
        hostname="PSA-OT-MES01",
        description="Ubuntu 24.04 - servidor Linux real do lab, unido ao dominio via SSSD (Fase 1).",
    ),
]


async def seed_real_assets() -> int:
    async with SessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        ).scalar_one_or_none()
        if not tenant:
            print(f"Tenant '{TENANT_SLUG}' nao encontrado - rode 'app.seed' primeiro. Abortando.")
            return 0

        sector = (
            await session.execute(
                select(Sector).where(Sector.tenant_id == tenant.id, Sector.name == SECTOR_NAME)
            )
        ).scalar_one_or_none()
        if not sector:
            print(f"Setor '{SECTOR_NAME}' nao encontrado - rode o import do CMDB primeiro. Abortando.")
            return 0

        created = 0
        for data in REAL_ASSETS:
            existing = (
                await session.execute(
                    select(Asset).where(Asset.tenant_id == tenant.id, Asset.name == data["name"])
                )
            ).scalar_one_or_none()
            if existing:
                print(f"[=] Ativo ja existe: {data['name']}")
                continue
            session.add(Asset(
                tenant_id=tenant.id,
                sector_id=sector.id,
                status=AssetStatus.Active,
                **data,
            ))
            created += 1
            print(f"[+] Ativo criado: {data['name']}")

        await session.commit()
        print(f"OK: {created} ativo(s) real(is) criado(s) no CMDB.")
        return created


if __name__ == "__main__":
    asyncio.run(seed_real_assets())
