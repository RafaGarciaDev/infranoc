"""CMDB - Ativos (Fase 4 - Bloco 2)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_session
from app.core.deps import require
from app.domain.enums import AssetStatus, AssetType, Criticality, Layer
from app.domain.models import Alert, Asset

router = APIRouter(prefix="/assets", tags=["assets"])


# =============================================================================
# Schemas
# =============================================================================
class AssetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    display_name: str | None = None
    description: str | None = None
    type: AssetType
    layer: Layer
    site: str = Field(..., min_length=1, max_length=32)
    location: str | None = None
    status: AssetStatus = AssetStatus.Active
    criticality: Criticality = Criticality.Medium
    ip_address: str | None = None
    hostname: str | None = None
    owner_email: str | None = None
    owner_team: str | None = None
    parent_id: uuid.UUID | None = None
    metadata_json: dict | None = None


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    """Update parcial - todos os campos opcionais."""
    display_name: str | None = None
    description: str | None = None
    type: AssetType | None = None
    layer: Layer | None = None
    site: str | None = None
    location: str | None = None
    status: AssetStatus | None = None
    criticality: Criticality | None = None
    ip_address: str | None = None
    hostname: str | None = None
    owner_email: str | None = None
    owner_team: str | None = None
    parent_id: uuid.UUID | None = None
    metadata_json: dict | None = None


class AssetOut(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str | None
    description: str | None
    type: AssetType
    layer: Layer
    site: str
    location: str | None
    status: AssetStatus
    criticality: Criticality
    ip_address: str | None
    hostname: str | None
    owner_email: str | None
    owner_team: str | None
    parent_id: uuid.UUID | None
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class AssetSummary(BaseModel):
    """Formato leve pra listar children/parent."""
    id: uuid.UUID
    name: str
    type: AssetType
    status: AssetStatus

    model_config = {"from_attributes": True}


class AssetDetail(AssetOut):
    parent: AssetSummary | None
    children: list[AssetSummary]


# =============================================================================
# Helpers
# =============================================================================
def _tenant_id(claims: dict) -> uuid.UUID:
    return uuid.UUID(claims["tenant_id"])


# =============================================================================
# GET /api/assets
# =============================================================================
@router.get("", response_model=list[AssetOut])
async def list_assets(
    claims: Annotated[dict, Depends(require("cmdb.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    type_: AssetType | None = Query(None, alias="type"),
    layer: Layer | None = Query(None),
    site: str | None = Query(None),
    status_filter: AssetStatus | None = Query(None, alias="status"),
    criticality: Criticality | None = Query(None),
    parent_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None, description="busca em name, hostname, ip"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[AssetOut]:
    tenant_id = _tenant_id(claims)
    stmt = select(Asset).where(Asset.tenant_id == tenant_id)

    if type_:
        stmt = stmt.where(Asset.type == type_)
    if layer:
        stmt = stmt.where(Asset.layer == layer)
    if site:
        stmt = stmt.where(Asset.site == site)
    if status_filter:
        stmt = stmt.where(Asset.status == status_filter)
    if criticality:
        stmt = stmt.where(Asset.criticality == criticality)
    if parent_id:
        stmt = stmt.where(Asset.parent_id == parent_id)
    if search:
        pat = f"%{search}%"
        stmt = stmt.where(
            or_(
                Asset.name.ilike(pat),
                Asset.hostname.ilike(pat),
                Asset.ip_address.ilike(pat),
            )
        )

    stmt = stmt.order_by(Asset.name).limit(limit).offset(offset)
    rows = (await session.execute(stmt)).scalars().all()
    return [AssetOut.model_validate(r) for r in rows]


# =============================================================================
# GET /api/assets/{id}
# =============================================================================
@router.get("/{asset_id}", response_model=AssetDetail)
async def get_asset(
    asset_id: uuid.UUID,
    claims: Annotated[dict, Depends(require("cmdb.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AssetDetail:
    tenant_id = _tenant_id(claims)
    row = (
        await session.execute(
            select(Asset)
            .where(Asset.id == asset_id, Asset.tenant_id == tenant_id)
            .options(selectinload(Asset.parent), selectinload(Asset.children))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ativo nao encontrado")
    return AssetDetail.model_validate(row)


# =============================================================================
# POST /api/assets
# =============================================================================
@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
async def create_asset(
    payload: AssetCreate,
    claims: Annotated[dict, Depends(require("cmdb.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AssetOut:
    tenant_id = _tenant_id(claims)
    actor = claims.get("sub")

    # Se tem parent_id, valida que ele existe no mesmo tenant
    if payload.parent_id:
        parent = (
            await session.execute(
                select(Asset).where(
                    Asset.id == payload.parent_id,
                    Asset.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not parent:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "parent_id nao encontrado ou pertence a outro tenant",
            )

    row = Asset(
        tenant_id=tenant_id,
        created_by=actor,
        **payload.model_dump(),
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ativo '{payload.name}' ja existe neste tenant",
        )
    await session.refresh(row)
    return AssetOut.model_validate(row)


# =============================================================================
# PUT /api/assets/{id}   (update parcial)
# =============================================================================
@router.put("/{asset_id}", response_model=AssetOut)
async def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    claims: Annotated[dict, Depends(require("cmdb.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AssetOut:
    tenant_id = _tenant_id(claims)
    actor = claims.get("sub")

    row = (
        await session.execute(
            select(Asset).where(
                Asset.id == asset_id,
                Asset.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ativo nao encontrado")

    # Se mudou parent_id, valida
    changes = payload.model_dump(exclude_unset=True)
    if "parent_id" in changes and changes["parent_id"]:
        if changes["parent_id"] == asset_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Ativo nao pode ser parent de si mesmo",
            )
        parent = (
            await session.execute(
                select(Asset).where(
                    Asset.id == changes["parent_id"],
                    Asset.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not parent:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "parent_id nao encontrado ou pertence a outro tenant",
            )

    for field, value in changes.items():
        setattr(row, field, value)
    row.updated_by = actor

    await session.commit()
    await session.refresh(row)
    return AssetOut.model_validate(row)


# =============================================================================
# DELETE /api/assets/{id}   (soft delete via status=Retired)
# =============================================================================
@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: uuid.UUID,
    claims: Annotated[dict, Depends(require("cmdb.admin"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    tenant_id = _tenant_id(claims)
    actor = claims.get("sub")
    row = (
        await session.execute(
            select(Asset).where(
                Asset.id == asset_id,
                Asset.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ativo nao encontrado")

    row.status = AssetStatus.Retired
    row.updated_by = actor
    await session.commit()

# =============================================================================
# GET /api/assets/{id}/alerts   (Fase 4 - Bloco 4: cross-link)
# =============================================================================
class AlertOfAssetOut(BaseModel):
    id: uuid.UUID
    alertname: str
    severity: str
    status: str
    summary: str | None
    starts_at: datetime
    ends_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("/{asset_id}/alerts", response_model=list[AlertOfAssetOut])
async def list_asset_alerts(
    asset_id: uuid.UUID,
    claims: Annotated[dict, Depends(require("cmdb.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
) -> list[AlertOfAssetOut]:
    """Retorna alertas cujo label asset bate com o name do ativo."""
    tenant_id = _tenant_id(claims)

    asset = (
        await session.execute(
            select(Asset).where(Asset.id == asset_id, Asset.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ativo nao encontrado")

    stmt = select(Alert).where(
        Alert.tenant_id == tenant_id,
        Alert.asset == asset.name,
    )
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter)
    stmt = stmt.order_by(Alert.starts_at.desc()).limit(limit)

    rows = (await session.execute(stmt)).scalars().all()
    return [AlertOfAssetOut.model_validate(r) for r in rows]