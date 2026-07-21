"""Hub de Acessos Diretos (Fase 9k).

Reune acessos rapidos aos ativos do CMDB que tem IP/hostname cadastrado:
- download de arquivo .rdp pronto (Windows Server/Workstation)
- comando SSH sugerido (ativos Linux/OT)
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application import audit_service
from app.core.db import get_session
from app.core.deps import require
from app.domain.models import Asset

router = APIRouter(prefix="/hub", tags=["hub-acessos"])


class HubAssetOut(BaseModel):
    id: str
    name: str
    hostname: str | None
    ip_address: str | None
    type: str
    site: str


@router.get("/acessos", response_model=list[HubAssetOut])
async def list_hub_assets(
    claims: Annotated[dict, Depends(require("cmdb.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[HubAssetOut]:
    tenant_id = uuid.UUID(claims["tenant_id"])
    stmt = (
        select(Asset)
        .where(Asset.tenant_id == tenant_id, Asset.type.in_(["Server", "Workstation"]))
        .order_by(Asset.name)
        .limit(500)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        HubAssetOut(
            id=str(a.id), name=a.name, hostname=a.hostname,
            ip_address=a.ip_address, type=a.type.value, site=a.site,
        )
        for a in rows
    ]


@router.get("/acessos/{asset_id}/rdp")
async def download_rdp(
    asset_id: str,
    claims: Annotated[dict, Depends(require("cmdb.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    tenant_id = uuid.UUID(claims["tenant_id"])
    asset = await session.get(Asset, uuid.UUID(asset_id))
    if not asset or asset.tenant_id != tenant_id:
        raise HTTPException(404, "Ativo nao encontrado")
    if asset.type.value not in ("Server", "Workstation"):
        raise HTTPException(400, "RDP disponivel apenas para Server/Workstation")

    target = asset.ip_address or asset.hostname or asset.name
    rdp_content = (
        f"full address:s:{target}\n"
        "username:s:INFRANOC\\\\admin\n"
        "audiomode:i:2\n"
        "redirectclipboard:i:1\n"
    )
    await audit_service.log(session, "acesso.direto.rdp", target=asset.hostname or asset.name)
    filename = (asset.hostname or asset.name).replace(" ", "_")
    return Response(
        content=rdp_content,
        media_type="application/x-rdp",
        headers={"Content-Disposition": f'attachment; filename="{filename}.rdp"'},
    )
