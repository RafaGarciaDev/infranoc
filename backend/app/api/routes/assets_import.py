"""Importador de ativos a partir do asset_simulator (Fase 4 - Bloco 3).

Faz scrape das metricas em formato Prometheus text e faz upsert dos ativos
no CMDB. Mapeia o `type` do simulador para AssetType/Layer/Criticality do
dominio, populando um catalogo rico sem input manual.
"""

from __future__ import annotations

import re
import time
import uuid
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require
from app.domain.enums import AssetStatus, AssetType, Criticality, Layer
from app.domain.models import Asset

router = APIRouter(prefix="/assets", tags=["assets"])


# =============================================================================
# Mapping: type do simulador -> (AssetType, Layer, Criticality)
# =============================================================================
TYPE_MAPPING: dict[str, tuple[AssetType, Layer, Criticality]] = {
    "server":            (AssetType.Server,        Layer.TI,       Criticality.High),
    "workstation":       (AssetType.Workstation,   Layer.TI,       Criticality.Low),
    "switch":            (AssetType.NetworkSwitch, Layer.TI,       Criticality.High),
    "ap":                (AssetType.AccessPoint,   Layer.TI,       Criticality.Medium),
    "printer":           (AssetType.Printer,       Layer.TI,       Criticality.Low),
    "camera":            (AssetType.Camera,        Layer.Physical, Criticality.Medium),
    "ups":               (AssetType.UPS,           Layer.Physical, Criticality.Critical),
    "plc":               (AssetType.PLC,           Layer.OT,       Criticality.High),
    "sensor_temp_cf":    (AssetType.Sensor,        Layer.OT,       Criticality.Critical),
    "sensor_temp_past":  (AssetType.Sensor,        Layer.OT,       Criticality.Critical),
    "hmi":               (AssetType.HMI,           Layer.OT,       Criticality.High),
    "scada":             (AssetType.SCADA,         Layer.OT,       Criticality.Critical),
}

HUMAN_TYPE: dict[str, str] = {
    "server":           "Servidor",
    "workstation":      "Workstation",
    "switch":           "Switch",
    "ap":               "Access Point",
    "printer":          "Impressora",
    "camera":           "Camera",
    "ups":              "UPS (No-Break)",
    "plc":              "CLP",
    "sensor_temp_cf":   "Sensor de Temperatura (Camara Fria)",
    "sensor_temp_past": "Sensor de Temperatura (Pasteurizacao)",
    "hmi":              "HMI",
    "scada":            "SCADA",
}


# =============================================================================
# Resolver de sim_type (labels do simulador sao ambiguas: 'network' cobre
# switch+AP, 'power' e UPS, 'temp' e sensor). Desambigua pelo nome do ativo.
# =============================================================================
def _resolve_sim_type(name: str, raw: str) -> str:
    n = name.upper()
    r = raw.lower().strip()
    if r == "network":
        if "-SW-" in n or n.startswith("PSA-NET-SW"):
            return "switch"
        if "-AP-" in n or n.startswith("PSA-NET-AP"):
            return "ap"
        return r
    if r == "power":
        return "ups"
    if r == "temp":
        if "-CF" in n:
            return "sensor_temp_cf"
        if "-PAST" in n:
            return "sensor_temp_past"
        return "sensor_temp_cf"
    return r


# =============================================================================
# Schemas
# =============================================================================
class ImportRequest(BaseModel):
    source_url: str = Field(
        default="http://localhost:9200/metrics",
        description="URL do endpoint /metrics do asset_simulator",
    )
    site_default: str = Field(
        default="PSA",
        description="Site atribuido se a metrica nao tiver label 'site'",
    )
    dry_run: bool = Field(
        default=False,
        description="Se true, so simula e retorna o que seria feito",
    )


class ImportError(BaseModel):
    asset: str | None
    reason: str


class ImportResult(BaseModel):
    source_url: str
    dry_run: bool
    scanned: int
    created: int
    updated: int
    skipped: int
    errors: list[ImportError]
    elapsed_ms: int


# =============================================================================
# Parser de metricas Prometheus (formato text)
# =============================================================================
_METRIC_LINE = re.compile(
    r'^infranoc_asset_up\{(?P<labels>[^}]+)\}\s+(?P<value>[\d.eE+-]+)\s*$'
)
_LABEL = re.compile(r'(\w+)="([^"]*)"')


def _parse_metrics(text: str) -> list[dict[str, str]]:
    """Extrai lista de labels de cada linha `infranoc_asset_up{...}`."""
    out: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _METRIC_LINE.match(line)
        if not m:
            continue
        labels_str = m.group("labels")
        labels = {k: v for k, v in _LABEL.findall(labels_str)}
        if "asset" not in labels:
            continue
        out.append(labels)
    return out


# =============================================================================
# POST /api/assets/import
# =============================================================================
@router.post("/import", response_model=ImportResult)
async def import_assets_from_simulator(
    payload: ImportRequest,
    claims: Annotated[dict, Depends(require("cmdb.admin"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ImportResult:
    started = time.perf_counter()
    tenant_id = uuid.UUID(claims["tenant_id"])
    actor = claims.get("sub")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(payload.source_url)
            r.raise_for_status()
            text = r.text
    except httpx.HTTPError as e:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Falha ao buscar metricas em {payload.source_url}: {e}",
        )

    rows = _parse_metrics(text)
    if not rows:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Nenhuma metrica 'infranoc_asset_up{...}' encontrada. "
            "Verifique se o source_url aponta pro asset-simulator.",
        )

    created = 0
    updated = 0
    skipped = 0
    errors: list[ImportError] = []

    existing_stmt = select(Asset).where(Asset.tenant_id == tenant_id)
    existing_rows = (await session.execute(existing_stmt)).scalars().all()
    existing_by_name = {a.name: a for a in existing_rows}

    for labels in rows:
        name = labels.get("asset", "").strip()
        sim_type = labels.get("type", "").strip().lower()
        site = labels.get("site", payload.site_default).strip() or payload.site_default

        if not name:
            skipped += 1
            errors.append(ImportError(asset=None, reason="asset vazio"))
            continue

        sim_type = _resolve_sim_type(name, sim_type)
        mapping = TYPE_MAPPING.get(sim_type)
        if mapping is None:
            skipped += 1
            errors.append(
                ImportError(asset=name, reason=f"type '{sim_type}' nao mapeado")
            )
            continue

        asset_type, layer, criticality = mapping
        human = HUMAN_TYPE.get(sim_type, sim_type)
        display_name = f"{human} {name}"
        description = f"Ativo importado do asset-simulator ({sim_type}) - site {site}."

        existing = existing_by_name.get(name)
        if existing is None:
            row = Asset(
                tenant_id=tenant_id,
                name=name,
                display_name=display_name,
                description=description,
                type=asset_type,
                layer=layer,
                site=site,
                status=AssetStatus.Active,
                criticality=criticality,
                owner_team=(
                    "OT" if layer == Layer.OT
                    else "Infra-Fisica" if layer == Layer.Physical
                    else "TI-Infra"
                ),
                metadata_json={
                    "source": "asset-simulator",
                    "sim_type": sim_type,
                    "labels": labels,
                },
                created_by=actor,
            )
            if not payload.dry_run:
                session.add(row)
            created += 1
        else:
            existing.type = asset_type
            existing.layer = layer
            existing.criticality = criticality
            if not existing.display_name:
                existing.display_name = display_name
            existing.metadata_json = {
                **(existing.metadata_json or {}),
                "source": "asset-simulator",
                "sim_type": sim_type,
                "last_labels": labels,
            }
            existing.updated_by = actor
            updated += 1

    if not payload.dry_run:
        await session.commit()

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return ImportResult(
        source_url=payload.source_url,
        dry_run=payload.dry_run,
        scanned=len(rows),
        created=created,
        updated=updated,
        skipped=skipped,
        errors=errors,
        elapsed_ms=elapsed_ms,
    )