"""Painel de Backup (Fase 9f) - dados simulados via seed.

Nao roda Veeam de verdade no lab (custo de infra alto). O cliente
VeeamClient real ficaria por tras de uma feature flag (use_real_veeam),
nao implementada aqui - ver ADR-003.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_session
from app.core.deps import require
from app.domain.models import BackupJob, RestorePoint

router = APIRouter(prefix="/backup", tags=["backup"])


class BackupJobOut(BaseModel):
    id: str
    name: str
    source: str
    target: str
    schedule: str
    retention_days: int
    rpo_target_hours: int
    rto_target_hours: int
    last_run: datetime | None
    last_status: str
    actual_rpo_hours: float | None
    rpo_exceeded: bool
    restore_point_count: int


class RestorePointOut(BaseModel):
    timestamp: datetime
    size_gb: float
    status: str
    expires_at: datetime | None


class BackupKpisOut(BaseModel):
    total_jobs: int
    jobs_ok: int
    jobs_failed: int
    jobs_rpo_exceeded: int


def _to_job_out(j: BackupJob, now: datetime) -> BackupJobOut:
    successful = [rp for rp in j.restore_points if rp.status == "success"]
    latest = max(successful, key=lambda rp: rp.timestamp) if successful else None
    actual_rpo = (now - latest.timestamp).total_seconds() / 3600 if latest else None
    rpo_exceeded = actual_rpo is not None and actual_rpo > j.rpo_target_hours
    return BackupJobOut(
        id=str(j.id), name=j.name, source=j.source, target=j.target, schedule=j.schedule,
        retention_days=j.retention_days, rpo_target_hours=j.rpo_target_hours, rto_target_hours=j.rto_target_hours,
        last_run=j.last_run, last_status=j.last_status,
        actual_rpo_hours=round(actual_rpo, 1) if actual_rpo is not None else None,
        rpo_exceeded=rpo_exceeded,
        restore_point_count=len(j.restore_points),
    )


@router.get("/jobs", response_model=list[BackupJobOut])
async def list_backup_jobs(
    claims: Annotated[dict, Depends(require("backup.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[BackupJobOut]:
    tenant_id = uuid.UUID(claims["tenant_id"])
    stmt = (
        select(BackupJob)
        .where(BackupJob.tenant_id == tenant_id)
        .options(selectinload(BackupJob.restore_points))
        .order_by(BackupJob.name)
    )
    rows = (await session.execute(stmt)).scalars().all()
    now = datetime.now(timezone.utc)
    return [_to_job_out(j, now) for j in rows]


@router.get("/jobs/{job_id}/restore-points", response_model=list[RestorePointOut])
async def list_restore_points(
    job_id: str,
    claims: Annotated[dict, Depends(require("backup.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[RestorePointOut]:
    tenant_id = uuid.UUID(claims["tenant_id"])
    job = await session.get(BackupJob, uuid.UUID(job_id))
    if not job or job.tenant_id != tenant_id:
        raise HTTPException(404, "Job de backup nao encontrado")
    stmt = (
        select(RestorePoint)
        .where(RestorePoint.job_id == job.id)
        .order_by(RestorePoint.timestamp.desc())
        .limit(50)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        RestorePointOut(timestamp=r.timestamp, size_gb=r.size_gb, status=r.status, expires_at=r.expires_at)
        for r in rows
    ]


@router.get("/kpis", response_model=BackupKpisOut)
async def get_backup_kpis(
    claims: Annotated[dict, Depends(require("backup.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BackupKpisOut:
    tenant_id = uuid.UUID(claims["tenant_id"])
    stmt = (
        select(BackupJob)
        .where(BackupJob.tenant_id == tenant_id)
        .options(selectinload(BackupJob.restore_points))
    )
    rows = (await session.execute(stmt)).scalars().all()
    now = datetime.now(timezone.utc)
    outs = [_to_job_out(j, now) for j in rows]
    return BackupKpisOut(
        total_jobs=len(outs),
        jobs_ok=sum(1 for o in outs if o.last_status == "success" and not o.rpo_exceeded),
        jobs_failed=sum(1 for o in outs if o.last_status == "failed"),
        jobs_rpo_exceeded=sum(1 for o in outs if o.rpo_exceeded),
    )
