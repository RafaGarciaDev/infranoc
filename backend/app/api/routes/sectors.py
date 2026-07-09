"""CMDB - Setores (Fase 4.5).

Lista setores produtivos (ISA-95 Level 3 - Area) com contadores agregados.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require
from app.domain.enums import AssetStatus
from app.domain.models import Alert, Asset, HierarchyLevel, Sector

router = APIRouter(prefix="/sectors", tags=["sectors"])


class SectorOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    oee_target: float | None
    assets_count: int
    equipments_count: int
    alerts_firing: int
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


def _tenant_id(claims: dict) -> uuid.UUID:
    return uuid.UUID(claims["tenant_id"])


@router.get("", response_model=list[SectorOut])
async def list_sectors(
    claims: Annotated[dict, Depends(require("cmdb.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[SectorOut]:
    tenant_id = _tenant_id(claims)

    sectors = (
        await session.execute(
            select(Sector).where(Sector.tenant_id == tenant_id).order_by(Sector.code)
        )
    ).scalars().all()

    # Contagens por setor em uma query so
    assets_counts = dict(
        (await session.execute(
            select(Asset.sector_id, func.count(Asset.id))
            .where(Asset.tenant_id == tenant_id, Asset.sector_id.is_not(None))
            .group_by(Asset.sector_id)
        )).all()
    )
    equipments_counts = dict(
        (await session.execute(
            select(Asset.sector_id, func.count(Asset.id))
            .where(
                Asset.tenant_id == tenant_id,
                Asset.sector_id.is_not(None),
                Asset.hierarchy_level == HierarchyLevel.Equipment,
                Asset.status == AssetStatus.Active,
            )
            .group_by(Asset.sector_id)
        )).all()
    )

    # Alertas firing agrupados por setor (via join asset.name = alert.asset)
    firing_counts = dict(
        (await session.execute(
            select(Asset.sector_id, func.count(Alert.id))
            .join(Alert, Alert.asset == Asset.name)
            .where(
                Asset.tenant_id == tenant_id,
                Alert.tenant_id == tenant_id,
                Asset.sector_id.is_not(None),
                Alert.status == "firing",
            )
            .group_by(Asset.sector_id)
        )).all()
    )

    out: list[SectorOut] = []
    for s in sectors:
        out.append(SectorOut(
            id=s.id,
            code=s.code,
            name=s.name,
            description=s.description,
            oee_target=s.oee_target,
            assets_count=assets_counts.get(s.id, 0),
            equipments_count=equipments_counts.get(s.id, 0),
            alerts_firing=firing_counts.get(s.id, 0),
            created_at=s.created_at,
            updated_at=s.updated_at,
        ))
    return out


@router.get("/{sector_id}", response_model=SectorOut)
async def get_sector(
    sector_id: uuid.UUID,
    claims: Annotated[dict, Depends(require("cmdb.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SectorOut:
    tenant_id = _tenant_id(claims)
    s = (
        await session.execute(
            select(Sector).where(Sector.id == sector_id, Sector.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Setor nao encontrado")

    assets_count = (await session.execute(
        select(func.count(Asset.id)).where(
            Asset.tenant_id == tenant_id, Asset.sector_id == s.id
        )
    )).scalar_one()
    equipments_count = (await session.execute(
        select(func.count(Asset.id)).where(
            Asset.tenant_id == tenant_id,
            Asset.sector_id == s.id,
            Asset.hierarchy_level == HierarchyLevel.Equipment,
            Asset.status == AssetStatus.Active,
        )
    )).scalar_one()
    firing = (await session.execute(
        select(func.count(Alert.id))
        .join(Asset, Asset.name == Alert.asset)
        .where(
            Alert.tenant_id == tenant_id,
            Asset.tenant_id == tenant_id,
            Asset.sector_id == s.id,
            Alert.status == "firing",
        )
    )).scalar_one()

    return SectorOut(
        id=s.id,
        code=s.code,
        name=s.name,
        description=s.description,
        oee_target=s.oee_target,
        assets_count=assets_count,
        equipments_count=equipments_count,
        alerts_firing=firing,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )