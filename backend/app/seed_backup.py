"""Seed de jobs de backup ficticios (Fase 9f - painel simulado).

Rodar:  uv run python -m app.seed_backup
"""
import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.domain.models import BackupJob, RestorePoint, Tenant

TENANT_SLUG = "valeverde"

_JOBS = [
    dict(name="Backup diario PostgreSQL (InfraNOC)", source="postgres-dev", target="NAS-Backup-01",
         schedule="Diario 02:00", retention_days=30, rpo_target_hours=24, rto_target_hours=4, freq_hours=24),
    dict(name="Backup semanal Active Directory", source="PSA-TI-DC01", target="NAS-Backup-01",
         schedule="Semanal (Dom 01:00)", retention_days=90, rpo_target_hours=168, rto_target_hours=8, freq_hours=168),
    dict(name="Backup mensal completo (Full)", source="Todos os servidores", target="Storage Offsite",
         schedule="Mensal (dia 1, 00:00)", retention_days=365, rpo_target_hours=720, rto_target_hours=24, freq_hours=720),
    dict(name="Backup diario Peppermint (ITSM)", source="peppermint-postgres", target="NAS-Backup-01",
         schedule="Diario 03:00", retention_days=30, rpo_target_hours=24, rto_target_hours=2, freq_hours=24),
    dict(name="Backup diario Vikunja (Tarefas)", source="vikunja-postgres", target="NAS-Backup-01",
         schedule="Diario 03:15", retention_days=30, rpo_target_hours=24, rto_target_hours=2, freq_hours=24),
    dict(name="Snapshot CMDB (Ativos)", source="postgres-dev (assets)", target="NAS-Backup-01",
         schedule="Diario 02:30", retention_days=14, rpo_target_hours=24, rto_target_hours=1, freq_hours=24),
    dict(name="Backup dashboards Grafana", source="grafana-config", target="NAS-Backup-01",
         schedule="Semanal (Sab 04:00)", retention_days=60, rpo_target_hours=168, rto_target_hours=2, freq_hours=168),
    dict(name="Backup configs Prometheus/Alertmanager", source="observability-config", target="NAS-Backup-01",
         schedule="Semanal (Sab 04:15)", retention_days=60, rpo_target_hours=168, rto_target_hours=2, freq_hours=168),
    dict(name="Backup diario MES01 (Linux)", source="PSA-OT-MES01", target="NAS-Backup-01",
         schedule="Diario 01:30", retention_days=30, rpo_target_hours=24, rto_target_hours=6, freq_hours=24),
    dict(name="Snapshot de VMs (VMware)", source="VMware Workstation (todas as VMs)", target="Storage Offsite",
         schedule="Semanal (Seg 00:30)", retention_days=45, rpo_target_hours=168, rto_target_hours=12, freq_hours=168),
]


def _gerar_restore_points(job_id: uuid.UUID, freq_hours: int, retention_days: int, rnd: random.Random) -> list[RestorePoint]:
    agora = datetime.now(timezone.utc)
    janela_dias = min(retention_days * 2, 120)
    total_pontos = max(3, int((janela_dias * 24) / freq_hours))
    pontos = []
    for i in range(total_pontos):
        ts = agora - timedelta(hours=freq_hours * i)
        falhou = rnd.random() < 0.06
        status = "failed" if falhou else ("warning" if rnd.random() < 0.05 else "success")
        pontos.append(
            RestorePoint(
                job_id=job_id,
                timestamp=ts,
                size_gb=round(rnd.uniform(0.5, 45.0), 2),
                status=status,
                expires_at=ts + timedelta(days=retention_days),
            )
        )
    return pontos


async def seed_backup():
    rnd = random.Random(11)
    async with SessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        ).scalar_one_or_none()
        if not tenant:
            print("[ERRO] Tenant valeverde nao existe. Rode `uv run python -m app.seed` primeiro.")
            return

        existing = (
            await session.execute(select(BackupJob).where(BackupJob.tenant_id == tenant.id))
        ).scalars().all()
        if existing:
            print(f"[=] Ja existem {len(existing)} jobs de backup. Nada a fazer.")
            return

        agora = datetime.now(timezone.utc)
        for job_def in _JOBS:
            freq_hours = job_def.pop("freq_hours")
            falhou_recentemente = rnd.random() < 0.15
            job = BackupJob(
                tenant_id=tenant.id,
                last_run=agora - timedelta(hours=rnd.uniform(0, freq_hours)),
                last_status="failed" if falhou_recentemente else "success",
                **job_def,
            )
            session.add(job)
            await session.flush()
            pontos = _gerar_restore_points(job.id, freq_hours, job.retention_days, rnd)
            session.add_all(pontos)

        await session.commit()
        print(f"[+] {len(_JOBS)} jobs de backup criados, com historico de restore points.")


if __name__ == "__main__":
    asyncio.run(seed_backup())
