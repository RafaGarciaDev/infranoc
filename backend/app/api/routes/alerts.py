"""Alertas vindos do AlertManager (Fase 3 - Bloco 4)."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_session
from app.core.config import settings
from app.core.deps import require
from app.domain.models import Alert, AlertStatusChange, Asset, Tenant

router = APIRouter(prefix="/alerts", tags=["alerts"])


# -----------------------------------------------------------------------------
# Basic Auth do webhook do AlertManager
# -----------------------------------------------------------------------------
_basic = HTTPBasic(auto_error=True)


def verify_am_basic_auth(
    credentials: Annotated[HTTPBasicCredentials, Depends(_basic)],
) -> str:
    """Valida usuario/senha do AlertManager via env vars.

    Defaults sao aceitos apenas no lab; em prod as duas envs devem existir.
    """
    expected_user = settings.alertmanager_webhook_user
    expected_pass = settings.alertmanager_webhook_pass

    ok_user = secrets.compare_digest(
        credentials.username.encode("utf-8"), expected_user.encode("utf-8")
    )
    ok_pass = secrets.compare_digest(
        credentials.password.encode("utf-8"), expected_pass.encode("utf-8")
    )
    if not (ok_user and ok_pass):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Credenciais invalidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# -----------------------------------------------------------------------------
# Schemas do payload do AlertManager
# https://prometheus.io/docs/alerting/latest/configuration/#webhook_config
# -----------------------------------------------------------------------------
class AmAlert(BaseModel):
    status: Literal["firing", "resolved"]
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: datetime
    endsAt: datetime | None = None
    generatorURL: str | None = None
    fingerprint: str


class AmPayload(BaseModel):
    version: str
    groupKey: str | None = None
    receiver: str | None = None
    status: Literal["firing", "resolved"]
    alerts: list[AmAlert]


# -----------------------------------------------------------------------------
# Schemas de resposta
# -----------------------------------------------------------------------------
class AlertStatusChangeOut(BaseModel):
    from_status: str | None
    to_status: str
    changed_at: datetime
    note: str | None

    model_config = {"from_attributes": True}


class AlertOut(BaseModel):
    id: uuid.UUID
    alertname: str
    asset: str | None
    severity: str
    categoria: str | None
    summary: str | None
    impacto_negocio: str | None
    status: str
    starts_at: datetime
    ends_at: datetime | None
    acknowledged_at: datetime | None
    acknowledged_by: str | None

    model_config = {"from_attributes": True}


class AlertDetailOut(AlertOut):
    fingerprint: str
    generator_url: str | None
    labels: dict | None
    annotations: dict | None
    asset_id: uuid.UUID | None = None
    status_history: list[AlertStatusChangeOut]


class WebhookResult(BaseModel):
    received: int
    created: int
    updated: int
    status_changes: int


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
async def _resolve_tenant(session: AsyncSession, slug: str) -> Tenant:
    tenant = (
        await session.execute(select(Tenant).where(Tenant.slug == slug))
    ).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Tenant '{slug}' nao encontrado")
    if not tenant.active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Tenant '{slug}' inativo")
    return tenant


# -----------------------------------------------------------------------------
# POST /api/alerts/webhook/{tenant_slug}
# -----------------------------------------------------------------------------
@router.post(
    "/webhook/{tenant_slug}",
    response_model=WebhookResult,
    dependencies=[Depends(verify_am_basic_auth)],
)
async def alertmanager_webhook(
    payload: AmPayload,
    tenant_slug: str = Path(..., pattern=r"^[a-z0-9-]{1,64}$"),
    session: AsyncSession = Depends(get_session),
) -> WebhookResult:
    tenant = await _resolve_tenant(session, tenant_slug)

    created = 0
    updated = 0
    status_changes = 0

    for am in payload.alerts:
        # busca por (tenant_id, fingerprint) - unique constraint
        existing = (
            await session.execute(
                select(Alert).where(
                    Alert.tenant_id == tenant.id,
                    Alert.fingerprint == am.fingerprint,
                )
            )
        ).scalar_one_or_none()

        new_status = am.status
        labels = am.labels or {}
        annotations = am.annotations or {}

        alertname = labels.get("alertname") or "unknown"
        asset = labels.get("asset") or labels.get("instance")
        severity = labels.get("severity") or "info"
        categoria = labels.get("categoria")
        summary = annotations.get("summary")
        impacto_negocio = annotations.get("impacto_negocio")

        if existing is None:
            row = Alert(
                tenant_id=tenant.id,
                fingerprint=am.fingerprint,
                alertname=alertname,
                asset=asset,
                severity=severity,
                categoria=categoria,
                summary=summary,
                impacto_negocio=impacto_negocio,
                generator_url=am.generatorURL,
                status=new_status,
                starts_at=am.startsAt,
                ends_at=am.endsAt if new_status == "resolved" else None,
                labels=labels,
                annotations=annotations,
            )
            session.add(row)
            await session.flush()
            session.add(
                AlertStatusChange(
                    alert_id=row.id,
                    from_status=None,
                    to_status=new_status,
                    note="inicial via webhook",
                )
            )
            created += 1
            status_changes += 1
        else:
            # atualiza sempre labels/annotations/generator (podem enriquecer)
            existing.labels = labels
            existing.annotations = annotations
            existing.summary = summary
            existing.impacto_negocio = impacto_negocio
            existing.severity = severity
            existing.categoria = categoria
            existing.generator_url = am.generatorURL

            if new_status != existing.status:
                session.add(
                    AlertStatusChange(
                        alert_id=existing.id,
                        from_status=existing.status,
                        to_status=new_status,
                        note="webhook",
                    )
                )
                existing.status = new_status
                if new_status == "resolved":
                    existing.ends_at = am.endsAt or datetime.now(am.startsAt.tzinfo)
                else:
                    existing.ends_at = None
                status_changes += 1
            updated += 1

    await session.commit()
    return WebhookResult(
        received=len(payload.alerts),
        created=created,
        updated=updated,
        status_changes=status_changes,
    )


# -----------------------------------------------------------------------------
# GET /api/alerts   (listagem)
# -----------------------------------------------------------------------------
_SEVERITY_ORDER = {"critical": 0, "high": 1, "warning": 2, "info": 3}


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    claims: dict = Depends(require("alerts.read")),
    session: AsyncSession = Depends(get_session),
    status_filter: Literal["firing", "resolved"] | None = Query(None, alias="status"),
    severity: str | None = Query(None),
    categoria: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[AlertOut]:
    tenant_id = uuid.UUID(claims["tenant_id"])

    stmt = select(Alert).where(Alert.tenant_id == tenant_id)
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if categoria:
        stmt = stmt.where(Alert.categoria == categoria)

    stmt = stmt.order_by(Alert.starts_at.desc()).limit(limit).offset(offset)
    rows = (await session.execute(stmt)).scalars().all()

    # ordena in-memory por severidade (firing primeiro, depois severidade)
    rows_sorted = sorted(
        rows,
        key=lambda r: (
            0 if r.status == "firing" else 1,
            _SEVERITY_ORDER.get(r.severity, 99),
            -r.starts_at.timestamp(),
        ),
    )
    return [AlertOut.model_validate(r) for r in rows_sorted]


# -----------------------------------------------------------------------------
# GET /api/alerts/{id}   (detalhe com historico)
# -----------------------------------------------------------------------------
@router.get("/{alert_id}", response_model=AlertDetailOut)
async def get_alert(
    alert_id: uuid.UUID,
    claims: dict = Depends(require("alerts.read")),
    session: AsyncSession = Depends(get_session),
) -> AlertDetailOut:
    tenant_id = uuid.UUID(claims["tenant_id"])
    row = (
        await session.execute(
            select(Alert)
            .where(Alert.id == alert_id, Alert.tenant_id == tenant_id)
            .options(selectinload(Alert.status_history))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alerta nao encontrado")

    # cross-link com CMDB (Fase 4 - Bloco 4): se row.asset bate com Asset.name, expoe asset_id
    asset_id_lookup: uuid.UUID | None = None
    if row.asset:
        asset_id_lookup = (
            await session.execute(
                select(Asset.id).where(
                    Asset.tenant_id == tenant_id,
                    Asset.name == row.asset,
                )
            )
        ).scalar_one_or_none()

    out = AlertDetailOut.model_validate(row)
    out.asset_id = asset_id_lookup
    return out