"""Servico de agregacao do Dashboard NOC (Fase 6).

Combina:
- OEE por linha (Prometheus: infranoc_oee_percent{line})
- Status de linha (infranoc_line_running - 0 == parada)
- Producao acumulada (sum(infranoc_units_produced_total))
- Ativos up/down (count(infranoc_asset_up == {0,1}))
- Alertas ativos do tenant (Postgres)
- Severidade agregada por area do mapa (heatmap da planta)
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Alert
from app.infrastructure.prometheus_client import PrometheusClient

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Linhas de envase (label `line` no Prometheus e sufixo L{n} nos ativos)
LINHAS: dict[int, str] = {
    1: "L1 UHT Leite",
    2: "L2 Iogurte",
    3: "L3 Queijo Frescal",
    4: "L4 Manteiga",
}

# Pesos de severidade (maior = pior). Alertas com severidade desconhecida = 0.
SEV_WEIGHT: dict[str, int] = {"critical": 4, "high": 3, "warning": 2, "info": 1}
SEV_NAME: dict[int, str] = {4: "critical", 3: "high", 2: "warning", 1: "info", 0: "ok"}

# Areas do mapa (11 - ISA-95 + linhas explodidas + datacenter + laboratorio).
# Ordem importa: e a ordem que o frontend vai renderizar por padrao.
_AREAS: dict[str, str] = {
    "recebimento": "Recebimento",
    "pasteurizacao": "Pasteurizacao",
    "laboratorio": "Laboratorio",
    "linha1": "Linha 1 UHT",
    "linha2": "Linha 2 Iogurte",
    "linha3": "Linha 3 Queijo Frescal",
    "linha4": "Linha 4 Manteiga",
    "camaras": "Camaras Frias",
    "expedicao": "Expedicao",
    "utilidades": "Utilidades",
    "datacenter": "Datacenter",
}


def _area_of_asset(name: str | None) -> str | None:
    """Mapeia nome de ativo (padrao PSA-{AREA}-...) para key do mapa.

    Nomenclatura real (Fase 4.5):
      PSA-RECEB-*, PSA-PAST-*, PSA-LAB-*, PSA-CF-*, PSA-EXPED-*,
      PSA-UTIL-*, PSA-DC-*, PSA-ENV-L{1..4}-*
    """
    if not name:
        return None
    parts = name.upper().split("-")
    if len(parts) < 2:
        return None

    area = parts[1]
    if area == "ENV" and len(parts) >= 3 and parts[2].startswith("L"):
        try:
            n = int(parts[2][1:])
        except ValueError:
            return None
        if 1 <= n <= 4:
            return f"linha{n}"
        return None

    return {
        "RECEB": "recebimento",
        "PAST": "pasteurizacao",
        "LAB": "laboratorio",
        "CF": "camaras",
        "EXPED": "expedicao",
        "UTIL": "utilidades",
        "DC": "datacenter",
    }.get(area)


# ---------------------------------------------------------------------------
# Agregacoes
# ---------------------------------------------------------------------------

async def overview(session: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Payload principal do dashboard: OEE, ativos, alertas, producao."""
    prom = PrometheusClient()

    # OEE + estado de cada linha
    oee: list[dict] = []
    for line_id, line_name in LINHAS.items():
        value = await prom.query_scalar(
            f'infranoc_oee_percent{{line="{line_id}"}}'
        )
        running = await prom.query_scalar(
            f'infranoc_line_running{{line="{line_id}"}}'
        )
        # running ausente => linha desconhecida => considera parada
        stopped = running is None or int(running) == 0
        oee.append({
            "line": line_id,
            "name": line_name,
            "value": round(value or 0.0, 1),
            "stopped": stopped,
        })

    # Contagem de ativos (count() sem match retorna vazio, tratamos como 0)
    up = await prom.query_scalar("count(infranoc_asset_up == 1)")
    down = await prom.query_scalar("count(infranoc_asset_up == 0)")
    output = await prom.query_scalar("sum(infranoc_units_produced_total)")

    # Alertas ativos do tenant
    active_rows = (await session.execute(
        select(Alert).where(
            Alert.tenant_id == tenant_id,
            Alert.status == "firing",
        )
    )).scalars().all()

    by_severity: dict[str, int] = {}
    for a in active_rows:
        by_severity[a.severity] = by_severity.get(a.severity, 0) + 1

    top = sorted(
        active_rows,
        key=lambda a: SEV_WEIGHT.get(a.severity, 0),
        reverse=True,
    )[:5]

    return {
        "oee": oee,
        "assets_up": int(up or 0),
        "assets_down": int(down or 0),
        "alerts_by_severity": by_severity,
        "alerts_active_total": len(active_rows),
        "top_alerts": [
            {
                "id": str(a.id),
                "summary": a.summary,
                "asset": a.asset,
                "severity": a.severity,
                "categoria": a.categoria,
                "impacto_negocio": a.impacto_negocio,
                "starts_at": a.starts_at.isoformat(),
            }
            for a in top
        ],
        "output_units": int(output or 0),
        "top_ti_alerts": [
            {
                "id": str(a.id),
                "summary": a.summary,
                "asset": a.asset,
                "severity": a.severity,
                "impacto_negocio": a.impacto_negocio,
                "starts_at": a.starts_at.isoformat(),
            }
            for a in sorted(
                [a for a in active_rows if (a.categoria or "").upper() == "TI"],
                key=lambda a: (SEV_WEIGHT.get(a.severity, 0), a.starts_at.timestamp()),
                reverse=True,
            )[:20]
        ],
    }


async def plant_status(session: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Retorna a pior severidade e contagem de alertas por area do mapa."""
    active_rows = (await session.execute(
        select(Alert).where(
            Alert.tenant_id == tenant_id,
            Alert.status == "firing",
        )
    )).scalars().all()

    worst: dict[str, int] = {}
    count: dict[str, int] = {}
    for a in active_rows:
        area = _area_of_asset(a.asset)
        if area is None:
            continue
        weight = SEV_WEIGHT.get(a.severity, 0)
        if weight > worst.get(area, 0):
            worst[area] = weight
        count[area] = count.get(area, 0) + 1

    return {
        "areas": [
            {
                "key": key,
                "label": label,
                "severity": SEV_NAME.get(worst.get(key, 0), "ok"),
                "count": count.get(key, 0),
            }
            for key, label in _AREAS.items()
        ]
    }