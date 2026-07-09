"""Job APScheduler - coleta de eventos de seguranca da DC01 (Fase 5, Bloco 6).

Roda a cada `settings.ad_audit_interval_minutes` minutos e coleta os eventos
de seguranca do Windows Event Log da DC01 via PowerShell Remoting (WinRM):

  4740 - conta bloqueada
  4625 - falha de logon
  4728 - membro adicionado a grupo global de seguranca
  4726 - conta de usuario excluida

Cada evento e inserido em `AdAuditEvent`. A insercao e idempotente: verifica
se ja existe registro com mesmo (tenant_id, event_id, at, target_sam) antes
de inserir.

O job usa SessionLocal diretamente (fora de request FastAPI).
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.domain.models import AdAuditEvent
from app.infrastructure.ps_ad_ops import PsAdOps

logger = logging.getLogger(__name__)

_WATCHED_IDS = [4740, 4625, 4728, 4726]
_WINDOW_FACTOR = 1.2


def _build_script(minutes_back: int) -> str:
    ids_filter = ",".join(str(i) for i in _WATCHED_IDS)
    return f"""
Import-Module ActiveDirectory -ErrorAction SilentlyContinue
$start = (Get-Date).AddMinutes(-{minutes_back})
$events = Get-WinEvent -ComputerName localhost -FilterHashtable @{{
    LogName   = 'Security'
    Id        = {ids_filter}
    StartTime = $start
}} -ErrorAction SilentlyContinue

if (-not $events) {{
    Write-Output '[]'
    exit
}}

$result = $events | ForEach-Object {{
    $msg = $_.Message -replace '\\r?\\n',' '
    $targetSam = $null
    if ($msg -match 'Account Name:\\s+(\\S+)') {{
        $targetSam = $Matches[1]
    }}
    $actorSam = $null
    if ($msg -match 'Caller User Name:\\s+(\\S+)') {{
        $actorSam = $Matches[1]
    }}
    [PSCustomObject]@{{
        EventId   = $_.Id
        TimeUtc   = $_.TimeCreated.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        TargetSam = $targetSam
        ActorSam  = $actorSam
        Message   = $msg
    }}
}}
$result | ConvertTo-Json -Depth 3 -Compress
"""


def _dedup_key(event_id: int, time_utc: str, target_sam: str | None) -> str:
    raw = f"{event_id}|{time_utc}|{target_sam or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()[:8]


async def collect_ad_events() -> None:
    """Funcao async chamada pelo APScheduler (AsyncIOScheduler)."""
    logger.info("ad_audit_job: iniciando coleta de eventos da DC01")

    minutes_back = int(settings.ad_audit_interval_minutes * _WINDOW_FACTOR + 1)
    script = _build_script(minutes_back)

    ps = PsAdOps()
    try:
        with ps._client() as c:
            out, streams, had_error = c.execute_ps(script)
    except Exception as exc:
        logger.error("ad_audit_job: erro WinRM ao coletar eventos: %s", exc)
        return

    if had_error:
        errs = "; ".join(str(e) for e in streams.error)
        logger.error("ad_audit_job: PowerShell reportou erro: %s", errs)

    raw_output = (out or "").strip()
    if not raw_output or raw_output == "[]":
        logger.info("ad_audit_job: nenhum evento novo na DC01")
        return

    try:
        events = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        logger.error("ad_audit_job: falha ao parsear JSON: %s | output=%r", exc, raw_output[:200])
        return

    if isinstance(events, dict):
        events = [events]

    tenant_id = uuid.UUID(settings.ad_tenant_id)
    inserted = 0
    skipped = 0

    async with SessionLocal() as session:
        for ev in events:
            try:
                event_id = int(ev["EventId"])
                time_utc = ev["TimeUtc"]
                target_sam = ev.get("TargetSam") or None
                actor_sam = ev.get("ActorSam") or None
                message = ev.get("Message") or ""
                at = datetime.fromisoformat(time_utc.replace("Z", "+00:00"))
            except (KeyError, ValueError) as exc:
                logger.warning("ad_audit_job: evento malformado ignorado: %s | ev=%r", exc, ev)
                continue

            exists = await session.scalar(
                select(AdAuditEvent.id).where(
                    AdAuditEvent.tenant_id == tenant_id,
                    AdAuditEvent.event_id == event_id,
                    AdAuditEvent.at == at,
                    AdAuditEvent.target_sam == target_sam,
                ).limit(1)
            )
            if exists:
                skipped += 1
                continue

            session.add(AdAuditEvent(
                tenant_id=tenant_id,
                event_id=event_id,
                at=at,
                target_sam=target_sam,
                actor_sam=actor_sam,
                message=message[:4000],
                raw=ev,
            ))
            inserted += 1

        await session.commit()

    logger.info(
        "ad_audit_job: coleta concluida — inseridos=%d ignorados=%d",
        inserted,
        skipped,
    )