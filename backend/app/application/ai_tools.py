# app/application/ai_tools.py
import uuid
from app.domain.enums import AssetType
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Asset, Alert
from app.infrastructure.prometheus_client import PrometheusClient


async def buscar_ativos(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    tipo: str | None = None,
    site: str | None = None,
    criticidade: str | None = None,
):
    stmt = select(Asset).where(Asset.tenant_id == tenant_id)
    if tipo:
        tipo_enum = _normalizar_tipo(tipo)
        if tipo_enum is not None:
            stmt = stmt.where(Asset.type == tipo_enum)
    if site:
        stmt = stmt.where(Asset.site == site)
    if criticidade:
        stmt = stmt.where(Asset.criticality == criticidade)
    rows = (await session.execute(stmt.limit(50))).scalars().all()
    return {
        "total": len(rows),
        "ativos": [
        {
            "hostname": a.hostname,
            "name": a.name,
            "type": str(a.type),
            "site": a.site,
            "location": a.location,
            "criticality": str(a.criticality),
            "owner_team": a.owner_team,
        }
            for a in rows
        ],
    }


async def consultar_alertas(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    categoria: str | None = None,
    dias: int = 7,
):
    since = datetime.now(timezone.utc) - timedelta(days=dias)
    stmt = select(Alert).where(Alert.tenant_id == tenant_id, Alert.starts_at >= since)
    if categoria:
        stmt = stmt.where(Alert.categoria == categoria)
    rows = (await session.execute(stmt)).scalars().all()
    by_sev: dict[str, int] = {}
    by_cat: dict[str, int] = {}
    for a in rows:
        by_sev[a.severity] = by_sev.get(a.severity, 0) + 1
        if a.categoria:
            by_cat[a.categoria] = by_cat.get(a.categoria, 0) + 1
    return {
        "total": len(rows),
        "por_severidade": by_sev,
        "por_categoria": by_cat,
        "top": [
            {"summary": a.summary, "asset": a.asset, "severity": a.severity}
            for a in rows[:10]
        ],
    }


async def producao_resumo(session: AsyncSession, tenant_id: uuid.UUID, dias: int = 7):
    prom = PrometheusClient()
    nomes = {1: "UHT", 2: "Iogurte", 3: "Queijos", 4: "Manteiga"}
    res = []
    for linha_id in nomes:
        oee = await prom.query_scalar(f'avg_over_time(infranoc_oee{{line="{linha_id}"}}[{dias}d])')
        res.append({"linha": linha_id, "nome": nomes[linha_id], "oee_medio": round(oee or 0, 1)})
    return {"periodo_dias": dias, "linhas": res}


async def metrica_atual(session: AsyncSession, tenant_id: uuid.UUID, promql: str):
    prom = PrometheusClient()
    return {"valor": await prom.query_scalar(promql)}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_ativos",
            "description": "Busca ativos do CMDB por tipo/site/criticidade",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo": {"type": "string"},
                    "site": {"type": "string"},
                    "criticidade": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_alertas",
            "description": "Alertas por periodo/categoria",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": {"type": "string"},
                    "dias": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "producao_resumo",
            "description": "OEE medio por linha no periodo",
            "parameters": {
                "type": "object",
                "properties": {"dias": {"type": "integer"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "metrica_atual",
            "description": "Consulta uma metrica Prometheus (PromQL)",
            "parameters": {
                "type": "object",
                "properties": {"promql": {"type": "string"}},
                "required": ["promql"],
            },
        },
    },
]



_TIPO_MAP = {
    "servidor": "Server", "servidores": "Server", "server": "Server",
    "estacao": "Workstation", "desktop": "Workstation", "workstation": "Workstation",
    "notebook": "Laptop", "laptop": "Laptop",
    "switch": "NetworkSwitch", "networkswitch": "NetworkSwitch",
    "roteador": "Router", "router": "Router",
    "firewall": "Firewall",
    "access point": "AccessPoint", "accesspoint": "AccessPoint", "ap": "AccessPoint",
    "impressora": "Printer", "printer": "Printer",
    "nobreak": "UPS", "no-break": "UPS", "no break": "UPS", "ups": "UPS",
    "gerador": "Generator", "generator": "Generator",
    "ar condicionado": "ACUnit", "acunit": "ACUnit",
    "clp": "PLC", "plc": "PLC",
    "hmi": "HMI", "scada": "SCADA", "sensor": "Sensor",
}


def _normalizar_tipo(tipo: str) -> AssetType | None:
    chave = tipo.strip().lower()
    nome = _TIPO_MAP.get(chave)
    if nome is not None:
        return AssetType[nome]
    for membro in AssetType:
        if membro.value.lower() == chave or membro.name.lower() == chave:
            return membro
    return None
