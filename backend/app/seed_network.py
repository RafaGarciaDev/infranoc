"""Seed do Mapa de Rede (Fase 9h) - gera topologia heuristica sobre o CMDB existente.

Heuristica:
- Switches/routers do setor "Ti Datacenter" formam o nucleo (interligados em anel).
- Setores com switch proprio: o switch do setor sobe (uplink) para um switch do
  nucleo (round-robin), e os demais ativos do setor conectam no switch do proprio setor.
- Setores sem switch proprio (e ativos comuns do Ti Datacenter): conectam direto
  num switch do nucleo (round-robin).
"""
import asyncio
import itertools
import uuid

from sqlalchemy import select

from app.core.db import SessionLocal
from app.domain.enums import AssetType
from app.domain.models import Asset, NetworkLink, NetworkLinkType, Sector


CORE_SECTOR_NAME = "Ti Datacenter"


async def seed_network(tenant_id: uuid.UUID) -> int:
    async with SessionLocal() as session:
        existing = (
            await session.execute(select(NetworkLink).where(NetworkLink.tenant_id == tenant_id))
        ).scalars().first()
        if existing:
            print("Ja existem links de rede para este tenant - abortando (evita duplicar).")
            return 0

        sectors = (
            await session.execute(select(Sector).where(Sector.tenant_id == tenant_id))
        ).scalars().all()
        sector_by_id = {s.id: s for s in sectors}
        core_sector = next((s for s in sectors if s.name == CORE_SECTOR_NAME), None)
        if not core_sector:
            print(f"Setor '{CORE_SECTOR_NAME}' nao encontrado - abortando.")
            return 0

        assets = (
            await session.execute(select(Asset).where(Asset.tenant_id == tenant_id))
        ).scalars().all()

        net_types = (AssetType.NetworkSwitch, AssetType.Router)
        core_switches = [a for a in assets if a.sector_id == core_sector.id and a.type in net_types]
        if not core_switches:
            print("Nenhum switch/router no nucleo - abortando.")
            return 0

        links_to_create: list[tuple[uuid.UUID, uuid.UUID]] = []

        # 1) nucleo em anel
        for a, b in zip(core_switches, core_switches[1:] + core_switches[:1]):
            if a.id != b.id:
                links_to_create.append((a.id, b.id))

        core_cycle = itertools.cycle(core_switches)

        # 2) por setor
        for sector in sectors:
            sector_assets = [a for a in assets if a.sector_id == sector.id]
            if sector.id == core_sector.id:
                # ativos comuns do nucleo (nao-switch) conectam direto num switch do nucleo
                for a in sector_assets:
                    if a.type in net_types:
                        continue
                    hub = next(core_cycle)
                    links_to_create.append((a.id, hub.id))
                continue

            sector_switches = [a for a in sector_assets if a.type in net_types]
            others = [a for a in sector_assets if a.type not in net_types]

            if sector_switches:
                local_hub = sector_switches[0]
                # uplink do switch do setor para o nucleo
                uplink_target = next(core_cycle)
                links_to_create.append((local_hub.id, uplink_target.id))
                # demais switches do setor (se houver) conectam no hub local
                for extra_sw in sector_switches[1:]:
                    links_to_create.append((extra_sw.id, local_hub.id))
                # ativos comuns conectam no hub local
                for a in others:
                    links_to_create.append((a.id, local_hub.id))
            else:
                # sem switch proprio: cada ativo conecta direto num switch do nucleo
                for a in others:
                    hub = next(core_cycle)
                    links_to_create.append((a.id, hub.id))

        for asset_a_id, asset_b_id in links_to_create:
            session.add(NetworkLink(
                tenant_id=tenant_id, asset_a_id=asset_a_id, asset_b_id=asset_b_id,
                link_type=NetworkLinkType.Ethernet,
            ))

        await session.commit()
        print(f"OK: {len(links_to_create)} links de rede criados.")
        return len(links_to_create)


async def main() -> None:
    async with SessionLocal() as session:
        tenant_ids = (await session.execute(select(Asset.tenant_id).distinct())).scalars().all()
    for tid in tenant_ids:
        await seed_network(tid)


if __name__ == "__main__":
    asyncio.run(main())
