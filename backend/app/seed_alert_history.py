"""Seed de historico de alertas (30-90 dias) para o modo demo do InfraNOC.

Gera alertas passados (majoritariamente resolvidos, alguns reconhecidos),
referenciando ativos reais do CMDB, para que a tela de Alertas e a
auditoria nao aparecam vazias em uma demo publica.

Rodar:  uv run python -m app.seed_alert_history
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.domain.models import Alert, Asset, Tenant

TENANT_SLUG = "valeverde"
TOTAL_ALERTAS = 300
DIAS_JANELA = 90

_TEMPLATES = [
    ("AssetOffline", "TI", "warning", "Ativo {asset} nao esta respondendo ha {min}min.", "Verificar conectividade e servico."),
    ("LinhaDeProducaoParada", "OT", "warning", "Linha parada ha {min}min (motivo: {motivo}).", "Perda de producao mensuravel no OEE."),
    ("CamaraFriaTemperaturaAlta", "OT", "critical", "Temperatura da camara fria acima do limite ({temp}C).", "Risco de perda de produto (HACCP)."),
    ("UPSOnBattery", "Energia", "warning", "No-break {asset} operando em bateria.", "Risco de queda de energia se prolongar."),
    ("TonerLow", "TI", "info", "Impressora {asset} com toner abaixo de 10%%.", "Sem impacto imediato na operacao."),
    ("DomainControllerOffline", "AD", "critical", "Domain Controller {asset} nao responde.", "Autenticacao de usuarios pode falhar."),
    ("PLCFalha", "OT", "critical", "CLP {asset} reportou falha de comunicacao.", "Linha associada pode parar."),
    ("SwitchPortasAltas", "TI", "info", "Switch {asset} com utilizacao de portas acima de 90%%.", "Planejar expansao de rede."),
]

_MOTIVOS = ["troca de produto", "manutencao corretiva", "falta de insumo", "ajuste de linha"]


def _gerar_alertas(assets: list[Asset], tenant_id: uuid.UUID) -> list[Alert]:
    rnd = random.Random(42)
    agora = datetime.now(timezone.utc)
    alertas = []
    for i in range(TOTAL_ALERTAS):
        alertname, categoria, severity, msg_tpl, impacto = rnd.choice(_TEMPLATES)
        asset = rnd.choice(assets) if assets else None
        dias_atras = rnd.uniform(0, DIAS_JANELA)
        starts_at = agora - timedelta(days=dias_atras)

        duracao_min = rnd.randint(3, 240)
        resolved = rnd.random() < 0.85
        ends_at = starts_at + timedelta(minutes=duracao_min) if resolved else None

        acked = resolved and rnd.random() < 0.6
        acknowledged_at = starts_at + timedelta(minutes=rnd.randint(1, duracao_min)) if acked else None

        summary = msg_tpl.format(
            asset=asset.name if asset else "PSA-DESCONHECIDO",
            min=rnd.randint(2, 30),
            motivo=rnd.choice(_MOTIVOS),
            temp=round(rnd.uniform(-8, -2), 1),
        )

        alertas.append(
            Alert(
                tenant_id=tenant_id,
                fingerprint=f"demo-hist-{i:05d}",
                alertname=alertname,
                asset=asset.name if asset else None,
                severity=severity,
                categoria=categoria,
                summary=summary,
                impacto_negocio=impacto,
                status="resolved" if resolved else "firing",
                starts_at=starts_at,
                ends_at=ends_at,
                acknowledged_at=acknowledged_at,
                acknowledged_by="demo@valeverde.com" if acked else None,
            )
        )
    return alertas


async def seed_alert_history():
    async with SessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        ).scalar_one_or_none()
        if not tenant:
            print("[ERRO] Tenant valeverde nao existe. Rode 'uv run python -m app.seed' primeiro.")
            return

        existing = (
            await session.execute(
                select(Alert).where(Alert.tenant_id == tenant.id, Alert.fingerprint.like("demo-hist-%"))
            )
        ).scalars().all()
        if existing:
            print(f"[=] Historico ja existe ({len(existing)} registros). Nada a fazer.")
            print("    (para regerar, delete manualmente os registros com fingerprint LIKE demo-hist-%% antes)")
            return

        assets = (
            await session.execute(select(Asset).where(Asset.tenant_id == tenant.id).limit(500))
        ).scalars().all()
        if not assets:
            print("[AVISO] Nenhum ativo encontrado no CMDB; historico sera gerado sem referencia de asset real.")

        alertas = _gerar_alertas(assets, tenant.id)
        session.add_all(alertas)
        await session.commit()
        print(f"[+] {len(alertas)} alertas historicos criados (janela de {DIAS_JANELA} dias).")


if __name__ == "__main__":
    asyncio.run(seed_alert_history())
