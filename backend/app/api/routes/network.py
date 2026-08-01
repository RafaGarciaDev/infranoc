"""Mapa de Rede Interativo (Fase 9h) - grafo de topologia sobre o CMDB."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application import audit_service
from app.core.db import get_session
from app.core.deps import require
from app.domain.enums import AssetStatus, AssetType, Criticality, Layer
from app.domain.models import Asset, NetworkLink, NetworkLinkType

router = APIRouter(prefix="/network", tags=["network"])


class NetworkNodeOut(BaseModel):
    id: str
    name: str
    type: AssetType
    layer: Layer
    site: str
    status: AssetStatus
    criticality: Criticality
    sector_id: str | None
    ip_address: str | None


class NetworkLinkOut(BaseModel):
    id: str
    asset_a_id: str
    asset_b_id: str
    link_type: NetworkLinkType


class NetworkGraphOut(BaseModel):
    nodes: list[NetworkNodeOut]
    links: list[NetworkLinkOut]


@router.get("/graph", response_model=NetworkGraphOut)
async def get_network_graph(
    claims: Annotated[dict, Depends(require("cmdb.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NetworkGraphOut:
    tenant_id = uuid.UUID(claims["tenant_id"])

    assets = (
        await session.execute(select(Asset).where(Asset.tenant_id == tenant_id))
    ).scalars().all()
    links = (
        await session.execute(select(NetworkLink).where(NetworkLink.tenant_id == tenant_id))
    ).scalars().all()

    nodes = [
        NetworkNodeOut(
            id=str(a.id), name=a.display_name or a.name, type=a.type, layer=a.layer,
            site=a.site, status=a.status, criticality=a.criticality,
            sector_id=str(a.sector_id) if a.sector_id else None,
            ip_address=a.ip_address,
        )
        for a in assets
    ]
    links_out = [
        NetworkLinkOut(
            id=str(lk.id), asset_a_id=str(lk.asset_a_id), asset_b_id=str(lk.asset_b_id),
            link_type=lk.link_type,
        )
        for lk in links
    ]
    return NetworkGraphOut(nodes=nodes, links=links_out)


class NetworkLinkCreateIn(BaseModel):
    asset_a_id: str
    asset_b_id: str
    link_type: NetworkLinkType = NetworkLinkType.Ethernet


@router.post("/links", response_model=NetworkLinkOut, status_code=201)
async def create_network_link(
    body: NetworkLinkCreateIn,
    claims: Annotated[dict, Depends(require("cmdb.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NetworkLinkOut:
    tenant_id = uuid.UUID(claims["tenant_id"])
    asset_a_id = uuid.UUID(body.asset_a_id)
    asset_b_id = uuid.UUID(body.asset_b_id)

    if asset_a_id == asset_b_id:
        raise HTTPException(400, "Um ativo nao pode se conectar a si mesmo")

    for asset_id in (asset_a_id, asset_b_id):
        asset = await session.get(Asset, asset_id)
        if not asset or asset.tenant_id != tenant_id:
            raise HTTPException(404, f"Ativo {asset_id} nao encontrado")

    link = NetworkLink(
        tenant_id=tenant_id, asset_a_id=asset_a_id, asset_b_id=asset_b_id,
        link_type=body.link_type,
    )
    session.add(link)
    await audit_service.log(session, "network.link.create", target=str(link.id), tenant_id=tenant_id)
    await session.commit()
    await session.refresh(link)
    return NetworkLinkOut(
        id=str(link.id), asset_a_id=str(link.asset_a_id), asset_b_id=str(link.asset_b_id),
        link_type=link.link_type,
    )


@router.delete("/links/{link_id}")
async def delete_network_link(
    link_id: str,
    claims: Annotated[dict, Depends(require("cmdb.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    tenant_id = uuid.UUID(claims["tenant_id"])
    link = await session.get(NetworkLink, uuid.UUID(link_id))
    if not link or link.tenant_id != tenant_id:
        raise HTTPException(404, "Link nao encontrado")
    await audit_service.log(session, "network.link.delete", target=str(link.id), tenant_id=tenant_id)
    await session.delete(link)
    await session.commit()
    return {"ok": True}
