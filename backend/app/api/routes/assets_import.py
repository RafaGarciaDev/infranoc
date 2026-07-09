"""Importador de ativos (Fase 4.5).

Le metricas Prometheus do asset_simulator e faz upsert em cascata:
  1. Sectors (1 por area)
  2. Line assets sinteticos (1 por linha, hierarchy_level=Line)
  3. Equipment assets (1 por metrica, hierarchy_level=Equipment, parent = line asset)

Labels esperadas em cada linha `infranoc_asset_up{...}`:
  asset, site, area, area_code (opcional), linha, sim_type

Se area_code nao vier, derivamos como PSA-AREA-{area}.
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
from app.domain.models import Asset, HierarchyLevel, Sector

router = APIRouter(prefix="/assets", tags=["assets"])


# =============================================================================
# Mapping: sim_type do simulador -> (AssetType, Layer, Criticality)
# =============================================================================
TYPE_MAPPING: dict[str, tuple[AssetType, Layer, Criticality]] = {
    # TI
    "server":             (AssetType.Server,          Layer.TI,       Criticality.High),
    "workstation":        (AssetType.Workstation,     Layer.TI,       Criticality.Low),
    "switch":             (AssetType.NetworkSwitch,   Layer.TI,       Criticality.High),
    "router":             (AssetType.Router,          Layer.TI,       Criticality.Critical),
    "firewall":           (AssetType.Firewall,        Layer.TI,       Criticality.Critical),
    "wifi_ap":            (AssetType.AccessPoint,     Layer.TI,       Criticality.Medium),
    "printer":            (AssetType.Printer,         Layer.TI,       Criticality.Low),
    # Infra fisica
    "camera":             (AssetType.Camera,          Layer.Physical, Criticality.Medium),
    "ups":                (AssetType.UPS,             Layer.Physical, Criticality.Critical),
    "generator":          (AssetType.Generator,       Layer.Physical, Criticality.Critical),
    "air_conditioner":    (AssetType.ACUnit,          Layer.Physical, Criticality.Medium),
    # OT: controle
    "plc":                (AssetType.PLC,             Layer.OT,       Criticality.High),
    "hmi":                (AssetType.HMI,             Layer.OT,       Criticality.High),
    "scada":              (AssetType.SCADA,           Layer.OT,       Criticality.Critical),
    # OT: sensores
    "sensor_temp_cf":     (AssetType.Sensor,          Layer.OT,       Criticality.Critical),
    "sensor_temp_past":   (AssetType.Sensor,          Layer.OT,       Criticality.Critical),
    "sensor_press":       (AssetType.Sensor,          Layer.OT,       Criticality.High),
    "sensor_level":       (AssetType.Sensor,          Layer.OT,       Criticality.Medium),
    "sensor_flow":        (AssetType.Sensor,          Layer.OT,       Criticality.Medium),
    "sensor_vibr":        (AssetType.Sensor,          Layer.OT,       Criticality.Medium),
    # OT: rotativos e vasos
    "motor":              (AssetType.Motor,           Layer.OT,       Criticality.High),
    "tank":               (AssetType.Tank,            Layer.OT,       Criticality.High),
    "air_compressor":     (AssetType.AirCompressor,   Layer.OT,       Criticality.High),
    "steam_boiler":       (AssetType.SteamBoiler,     Layer.OT,       Criticality.Critical),
    "chilled_water_pump": (AssetType.ChilledWaterPump, Layer.OT,      Criticality.High),
    # Laboratorio / leitores
    "weighing_scale":     (AssetType.Scale,           Layer.OT,       Criticality.Medium),
    "lab_scale":          (AssetType.Scale,           Layer.Physical, Criticality.Low),
    "barcode_reader":     (AssetType.BarcodeReader,   Layer.OT,       Criticality.Low),
}

HUMAN_TYPE: dict[str, str] = {
    "server":             "Servidor",
    "workstation":        "Workstation",
    "switch":             "Switch",
    "router":             "Roteador",
    "firewall":           "Firewall",
    "wifi_ap":            "Access Point WiFi",
    "printer":            "Impressora",
    "camera":             "Camera",
    "ups":                "UPS (No-Break)",
    "generator":          "Gerador",
    "air_conditioner":    "Ar Condicionado",
    "plc":                "CLP",
    "hmi":                "HMI",
    "scada":              "SCADA",
    "sensor_temp_cf":     "Sensor Temp. Camara Fria",
    "sensor_temp_past":   "Sensor Temp. Pasteurizacao",
    "sensor_press":       "Sensor de Pressao",
    "sensor_level":       "Sensor de Nivel",
    "sensor_flow":        "Sensor de Vazao",
    "sensor_vibr":        "Sensor de Vibracao",
    "motor":              "Motor",
    "tank":               "Tanque",
    "air_compressor":     "Compressor de Ar",
    "steam_boiler":       "Caldeira",
    "chilled_water_pump": "Bomba de Agua Gelada",
    "weighing_scale":     "Balanca Industrial",
    "lab_scale":          "Balanca de Laboratorio",
    "barcode_reader":     "Leitor de Codigo de Barras",
}


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


class ImportErrorItem(BaseModel):
    asset: str | None
    reason: str


class ImportResult(BaseModel):
    source_url: str
    dry_run: bool
    scanned: int
    created: int
    updated: int
    skipped: int
    sectors_created: int
    sectors_updated: int
    lines_created: int
    lines_updated: int
    errors: list[ImportErrorItem]
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
        labels = dict(_LABEL.findall(m.group("labels")))
        if "asset" not in labels:
            continue
        out.append(labels)
    return out


# =============================================================================
# Helpers
# =============================================================================
def _short_from_asset_name(name: str) -> str | None:
    """PSA-PAST-L1-SENS-PR-01 -> PAST."""
    parts = name.split("-")
    return parts[1] if len(parts) >= 2 else None


def _line_asset_name(short: str, linha: str) -> str:
    return f"PSA-{short}-{linha}-LINE"


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

    # 1. Fetch metricas
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

    # 2. Carrega estado atual (setores, ativos)
    sectors_by_code: dict[str, Sector] = {
        s.code: s for s in (
            await session.execute(select(Sector).where(Sector.tenant_id == tenant_id))
        ).scalars().all()
    }
    assets_by_name: dict[str, Asset] = {
        a.name: a for a in (
            await session.execute(select(Asset).where(Asset.tenant_id == tenant_id))
        ).scalars().all()
    }

    sectors_created = 0
    sectors_updated = 0
    lines_created = 0
    lines_updated = 0
    created = 0
    updated = 0
    skipped = 0
    errors: list[ImportErrorItem] = []

    # 3. PASS 1: coletar setores e linhas unicas
    unique_sectors: dict[str, dict] = {}   # area_code -> {name, area_key}
    unique_lines: dict[str, dict] = {}     # line_name -> {sector_code, short, linha, site}

    for labels in rows:
        name = labels.get("asset", "").strip()
        area_key = labels.get("area", "").strip()
        area_code = labels.get("area_code", "").strip() or (
            f"PSA-AREA-{area_key}" if area_key else ""
        )
        linha = labels.get("linha", "").strip()
        site = labels.get("site", payload.site_default).strip() or payload.site_default

        if not name or not area_code or not linha:
            continue

        if area_code not in unique_sectors:
            unique_sectors[area_code] = {
                "name": area_key.replace("-", " ").title() if area_key else area_code,
                "area_key": area_key,
            }

        short = _short_from_asset_name(name)
        if not short:
            continue
        line_name = _line_asset_name(short, linha)
        if line_name not in unique_lines:
            unique_lines[line_name] = {
                "sector_code": area_code,
                "short": short,
                "linha": linha,
                "site": site,
            }

    # 4. Upsert setores
    for code, info in unique_sectors.items():
        existing = sectors_by_code.get(code)
        if existing is None:
            s = Sector(
                tenant_id=tenant_id,
                code=code,
                name=info["name"],
                description=f"Setor produtivo {info['name']} (ISA-95 Area).",
                created_by=actor,
            )
            if not payload.dry_run:
                session.add(s)
            sectors_by_code[code] = s
            sectors_created += 1
        else:
            if existing.name != info["name"] and info["name"]:
                existing.name = info["name"]
            existing.updated_by = actor
            sectors_updated += 1

    # Precisamos dos IDs dos setores para amarrar FKs. Flush intermediario.
    if not payload.dry_run:
        await session.flush()

    # 5. Upsert line assets
    for line_name, info in unique_lines.items():
        sector = sectors_by_code[info["sector_code"]]
        existing = assets_by_name.get(line_name)
        if existing is None:
            row = Asset(
                tenant_id=tenant_id,
                name=line_name,
                display_name=f"Linha {info['linha']} ({info['short']})",
                description=f"Linha de producao {info['linha']} - agrupamento logico ISA-95 Level 4.",
                type=AssetType.Other,
                layer=Layer.OT,
                site=info["site"],
                status=AssetStatus.Active,
                criticality=Criticality.Medium,
                sector_id=sector.id,
                hierarchy_level=HierarchyLevel.Line,
                owner_team="OT",
                metadata_json={
                    "source": "asset-simulator",
                    "synthetic": True,
                    "linha": info["linha"],
                    "short": info["short"],
                },
                created_by=actor,
            )
            if not payload.dry_run:
                session.add(row)
            assets_by_name[line_name] = row
            lines_created += 1
        else:
            existing.sector_id = sector.id
            existing.hierarchy_level = HierarchyLevel.Line
            existing.updated_by = actor
            lines_updated += 1

    if not payload.dry_run:
        await session.flush()

    # 6. PASS 2: upsert equipment assets
    for labels in rows:
        name = labels.get("asset", "").strip()
        sim_type = labels.get("sim_type", "").strip().lower()
        site = labels.get("site", payload.site_default).strip() or payload.site_default
        area_key = labels.get("area", "").strip()
        area_code = labels.get("area_code", "").strip() or (
            f"PSA-AREA-{area_key}" if area_key else ""
        )
        linha = labels.get("linha", "").strip()

        if not name:
            skipped += 1
            errors.append(ImportErrorItem(asset=None, reason="asset vazio"))
            continue

        mapping = TYPE_MAPPING.get(sim_type)
        if mapping is None:
            skipped += 1
            errors.append(
                ImportErrorItem(asset=name, reason=f"sim_type '{sim_type}' nao mapeado")
            )
            continue

        asset_type, layer, criticality = mapping
        human = HUMAN_TYPE.get(sim_type, sim_type)
        display_name = f"{human} {name}"
        description = f"Ativo importado do asset-simulator ({sim_type}) - site {site}."

        sector = sectors_by_code.get(area_code)
        short = _short_from_asset_name(name)
        parent = None
        if short and linha:
            parent = assets_by_name.get(_line_asset_name(short, linha))

        existing = assets_by_name.get(name)
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
                sector_id=sector.id if sector else None,
                hierarchy_level=HierarchyLevel.Equipment,
                parent_id=parent.id if parent else None,
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
            existing.sector_id = sector.id if sector else existing.sector_id
            existing.hierarchy_level = HierarchyLevel.Equipment
            if parent:
                existing.parent_id = parent.id
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
        sectors_created=sectors_created,
        sectors_updated=sectors_updated,
        lines_created=lines_created,
        lines_updated=lines_updated,
        errors=errors,
        elapsed_ms=elapsed_ms,
    )