"""Seed de eventos de seguranca simulados (Fase 9g - painel de SIEM).

Rodar:  uv run python -m app.seed_security
"""
import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.domain.models import SecurityEvent, Tenant

TENANT_SLUG = "valeverde"
TOTAL_EVENTOS = 180

_HOSTS = [
    "PSA-TI-DC01", "PSA-OT-MES01", "infranoc-backend", "infranoc-web",
    "infranoc-dev-postgres-1", "PSA-CF-CAM-PERIM-CAM-01", "PSA-UTIL-ENERGIA-UPS-07",
]

_TEMPLATES = [
    ("5710", "Multiplas tentativas de logon falharam", 10, "Credential Access", "T1110", "Brute Force"),
    ("5715", "Conta de usuario bloqueada apos falhas repetidas", 8, "Credential Access", "T1110.003", "Password Spraying"),
    ("530", "Falha de autenticacao SSH", 5, "Credential Access", "T1110", "Brute Force"),
    ("531", "Login SSH bem-sucedido apos multiplas falhas", 12, "Credential Access", "T1110", "Brute Force"),
    ("5501", "Novo usuario criado no sistema", 6, "Persistence", "T1136", "Create Account"),
    ("5502", "Usuario adicionado a grupo privilegiado", 9, "Privilege Escalation", "T1098", "Account Manipulation"),
    ("550", "Checksum de integridade de arquivo alterado", 7, "Defense Evasion", "T1070", "Indicator Removal"),
    ("100100", "Comando sudo suspeito executado", 8, "Privilege Escalation", "T1548", "Abuse Elevation Control Mechanism"),
    ("18152", "Regra do firewall do Windows modificada", 6, "Defense Evasion", "T1562", "Impair Defenses"),
    ("31151", "Padrao de varredura (scan) detectado no servidor web", 5, "Reconnaissance", "T1595", "Active Scanning"),
    ("1002", "Multiplas conexoes TCP para porta incomum", 6, "Discovery", "T1046", "Network Service Discovery"),
    ("5901", "Modulo de kernel carregado", 9, "Persistence", "T1547", "Boot or Logon Autostart Execution"),
]


def _gerar_eventos(tenant_id: uuid.UUID) -> list[SecurityEvent]:
    rnd = random.Random(23)
    agora = datetime.now(timezone.utc)
    eventos = []
    for _ in range(TOTAL_EVENTOS):
        rule_id, desc, level, tactic, tech_id, tech_name = rnd.choice(_TEMPLATES)
        host = rnd.choice(_HOSTS)
        dias_atras = rnd.uniform(0, 30)
        ts = agora - timedelta(days=dias_atras, hours=rnd.uniform(0, 23))
        eventos.append(
            SecurityEvent(
                tenant_id=tenant_id,
                timestamp=ts,
                source_host=host,
                rule_id=rule_id,
                rule_description=desc,
                level=level,
                mitre_tactic=tactic,
                mitre_technique_id=tech_id,
                mitre_technique_name=tech_name,
                raw_summary=f"[{host}] {desc} (rule {rule_id}, level {level})",
            )
        )
    return eventos


async def seed_security():
    async with SessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        ).scalar_one_or_none()
        if not tenant:
            print("[ERRO] Tenant valeverde nao existe. Rode 'uv run python -m app.seed' primeiro.")
            return

        existing = (
            await session.execute(select(SecurityEvent).where(SecurityEvent.tenant_id == tenant.id))
        ).scalars().all()
        if existing:
            print(f"[=] Ja existem {len(existing)} eventos de seguranca. Nada a fazer.")
            return

        eventos = _gerar_eventos(tenant.id)
        session.add_all(eventos)
        await session.commit()
        print(f"[+] {len(eventos)} eventos de seguranca criados (janela de 30 dias).")


if __name__ == "__main__":
    asyncio.run(seed_security())
