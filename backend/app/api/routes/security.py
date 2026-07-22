"""Painel de Seguranca / SIEM (Fase 9g) - dados simulados via seed.

Nao roda Wazuh de verdade no lab (custo de ~5GB RAM para Manager+Indexer+
Dashboard). Ver ADR-004 para a decisao completa.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require
from app.domain.models import SecurityEvent

router = APIRouter(prefix="/security", tags=["security"])


class SecurityEventOut(BaseModel):
    timestamp: datetime
    source_host: str
    rule_id: str
    rule_description: str
    level: int
    mitre_tactic: str
    mitre_technique_id: str
    mitre_technique_name: str


@router.get("/events", response_model=list[SecurityEventOut])
async def list_events(
    claims: Annotated[dict, Depends(require("security.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    level_min: int | None = None,
    host: str | None = None,
    limit: int = 100,
) -> list[SecurityEventOut]:
    tenant_id = uuid.UUID(claims["tenant_id"])
    stmt = select(SecurityEvent).where(SecurityEvent.tenant_id == tenant_id)
    if level_min is not None:
        stmt = stmt.where(SecurityEvent.level >= level_min)
    if host:
        stmt = stmt.where(SecurityEvent.source_host == host)
    stmt = stmt.order_by(SecurityEvent.timestamp.desc()).limit(min(limit, 500))
    rows = (await session.execute(stmt)).scalars().all()
    return [
        SecurityEventOut(
            timestamp=e.timestamp, source_host=e.source_host, rule_id=e.rule_id,
            rule_description=e.rule_description, level=e.level, mitre_tactic=e.mitre_tactic,
            mitre_technique_id=e.mitre_technique_id, mitre_technique_name=e.mitre_technique_name,
        )
        for e in rows
    ]


class TechniqueBreakdownOut(BaseModel):
    technique_id: str
    technique_name: str
    tactic: str
    count: int


class SecurityKpisOut(BaseModel):
    total_events: int
    critical_count: int
    high_count: int
    hosts_afetados: int
    top_techniques: list[TechniqueBreakdownOut]


@router.get("/kpis", response_model=SecurityKpisOut)
async def get_security_kpis(
    claims: Annotated[dict, Depends(require("security.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SecurityKpisOut:
    tenant_id = uuid.UUID(claims["tenant_id"])

    total = (await session.execute(
        select(func.count()).select_from(SecurityEvent).where(SecurityEvent.tenant_id == tenant_id)
    )).scalar_one()
    critical = (await session.execute(
        select(func.count()).select_from(SecurityEvent)
        .where(SecurityEvent.tenant_id == tenant_id, SecurityEvent.level >= 12)
    )).scalar_one()
    high = (await session.execute(
        select(func.count()).select_from(SecurityEvent)
        .where(SecurityEvent.tenant_id == tenant_id, SecurityEvent.level >= 8, SecurityEvent.level < 12)
    )).scalar_one()
    hosts = (await session.execute(
        select(func.count(func.distinct(SecurityEvent.source_host)))
        .where(SecurityEvent.tenant_id == tenant_id)
    )).scalar_one()

    breakdown_stmt = (
        select(
            SecurityEvent.mitre_technique_id, SecurityEvent.mitre_technique_name,
            SecurityEvent.mitre_tactic, func.count().label("cnt"),
        )
        .where(SecurityEvent.tenant_id == tenant_id)
        .group_by(SecurityEvent.mitre_technique_id, SecurityEvent.mitre_technique_name, SecurityEvent.mitre_tactic)
        .order_by(func.count().desc())
        .limit(10)
    )
    breakdown_rows = (await session.execute(breakdown_stmt)).all()

    return SecurityKpisOut(
        total_events=total, critical_count=critical, high_count=high, hosts_afetados=hosts,
        top_techniques=[
            TechniqueBreakdownOut(technique_id=r[0], technique_name=r[1], tactic=r[2], count=r[3])
            for r in breakdown_rows
        ],
    )
