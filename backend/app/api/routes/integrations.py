"""Rotas de configuracao de integracoes (Fase 6b).

Expoe:
  GET  /integrations                - configuracao efetiva do tenant (senha mascarada)
  PUT  /integrations                - atualiza campos informados (partial update)
  POST /integrations/test-connection - cria um ticket de teste no Peppermint

Seguranca: peppermint_password NUNCA e devolvida em texto puro no GET.
Se o campo estiver vazio no PUT (ou igual a mascara), a senha atual e preservada.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application import audit_service
from app.core.db import get_session
from app.core.deps import require
from app.domain.models import IntegrationSettings
from app.infrastructure.peppermint_client import PeppermintClient

router = APIRouter(prefix="/integrations", tags=["integrations"])
peppermint = PeppermintClient()

_PASSWORD_MASK = "********"


class IntegrationSettingsOut(BaseModel):
    peppermint_url: str | None
    peppermint_email: str | None
    peppermint_password: str | None
    peppermint_default_email: str | None
    peppermint_enabled: bool
    auto_ticket_min_severity: str
    storm_window_seconds: int
    storm_threshold: int
    updated_at: datetime | None
    updated_by: str | None


class IntegrationSettingsIn(BaseModel):
    peppermint_url: str | None = None
    peppermint_email: str | None = None
    peppermint_password: str | None = None
    peppermint_default_email: str | None = None
    peppermint_enabled: bool | None = None
    auto_ticket_min_severity: str | None = None
    storm_window_seconds: int | None = None
    storm_threshold: int | None = None


async def _get_or_create(session: AsyncSession, tenant_id: uuid.UUID) -> IntegrationSettings:
    row = (
        await session.execute(
            select(IntegrationSettings).where(IntegrationSettings.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if row is None:
        row = IntegrationSettings(tenant_id=tenant_id)
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row


def _to_out(row: IntegrationSettings) -> IntegrationSettingsOut:
    return IntegrationSettingsOut(
        peppermint_url=row.peppermint_url,
        peppermint_email=row.peppermint_email,
        peppermint_password=_PASSWORD_MASK if row.peppermint_password else None,
        peppermint_default_email=row.peppermint_default_email,
        peppermint_enabled=row.peppermint_enabled,
        auto_ticket_min_severity=row.auto_ticket_min_severity,
        storm_window_seconds=row.storm_window_seconds,
        storm_threshold=row.storm_threshold,
        updated_at=row.updated_at,
        updated_by=row.updated_by,
    )


@router.get("", response_model=IntegrationSettingsOut)
async def get_integrations(
    claims: dict = Depends(require("integrations.read")),
    session: AsyncSession = Depends(get_session),
) -> IntegrationSettingsOut:
    tenant_id = uuid.UUID(claims["tenant_id"])
    row = await _get_or_create(session, tenant_id)
    return _to_out(row)


@router.put("", response_model=IntegrationSettingsOut)
async def update_integrations(
    body: IntegrationSettingsIn,
    claims: dict = Depends(require("integrations.write")),
    session: AsyncSession = Depends(get_session),
) -> IntegrationSettingsOut:
    tenant_id = uuid.UUID(claims["tenant_id"])
    row = await _get_or_create(session, tenant_id)

    data = body.model_dump(exclude_unset=True)
    if "peppermint_password" in data:
        pw = data["peppermint_password"]
        if not pw or pw == _PASSWORD_MASK:
            data.pop("peppermint_password")

    for key, value in data.items():
        setattr(row, key, value)
    row.updated_by = claims.get("sub")

    await session.commit()
    await session.refresh(row)

    await audit_service.log(
        session,
        action="integrations.update",
        target="peppermint",
        details=f"fields={sorted(data.keys())}",
        tenant_id=tenant_id,
    )
    return _to_out(row)


@router.post("/test-connection")
async def test_connection(
    claims: dict = Depends(require("integrations.write")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    tenant_id = uuid.UUID(claims["tenant_id"])
    try:
        ticket_id = await peppermint.create_ticket(
            session,
            tenant_id,
            title="[TESTE] Conexao InfraNOC",
            detail="Ticket de teste gerado pela tela de Integracoes. Pode ser fechado/excluido manualmente.",
            priority="low",
        )
        await audit_service.log(
            session,
            action="integrations.test_connection",
            target=ticket_id,
            details="peppermint ok",
            tenant_id=tenant_id,
        )
        return {"ok": True, "message": f"Conexao OK. Ticket de teste #{ticket_id} criado no Peppermint."}
    except Exception as e:
        return {"ok": False, "message": str(e)}