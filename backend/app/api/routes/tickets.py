"""Rotas de consulta dos chamados abertos automaticamente (Fase 6b).

GET /tickets - lista TicketLink com dados do alerta (JOIN), achatados
              para o formato que a tela /chamados espera.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.core.deps import require
from app.domain.models import Alert, IntegrationSettings, TicketLink

router = APIRouter(prefix="/tickets", tags=["tickets"])


class TicketLinkOut(BaseModel):
    id: str
    alert_id: str | None
    alertname: str | None
    asset: str | None
    severity: str | None
    ticket_id: str
    ticket_url: str
    status: str
    created_at: datetime
    closed_at: datetime | None


@router.get("", response_model=list[TicketLinkOut])
async def list_tickets(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    claims: dict = Depends(require("tickets.read")),
    session: AsyncSession = Depends(get_session),
) -> list[TicketLinkOut]:
    tenant_id = uuid.UUID(claims["tenant_id"])

    q = (
        select(TicketLink, Alert.alertname, Alert.asset, Alert.severity)
        .outerjoin(Alert, Alert.id == TicketLink.alert_id)
        .where(
            TicketLink.tenant_id == tenant_id,
            TicketLink.peppermint_ticket_id.isnot(None),
        )
        .order_by(TicketLink.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status:
        q = q.where(TicketLink.status == status)

    rows = (await session.execute(q)).all()

    cfg = (
        await session.execute(
            select(IntegrationSettings).where(IntegrationSettings.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    base_url = (
        cfg.peppermint_url if cfg and cfg.peppermint_url else settings.peppermint_url
    ).rstrip("/")

    return [
        TicketLinkOut(
            id=str(link.id),
            alert_id=str(link.alert_id) if link.alert_id else None,
            alertname=alertname,
            asset=asset,
            severity=severity,
            ticket_id=link.peppermint_ticket_id,
            ticket_url=f"{base_url}/tickets/{link.peppermint_ticket_id}",
            status=link.status,
            created_at=link.created_at,
            closed_at=link.closed_at,
        )
        for link, alertname, asset, severity in rows
    ]