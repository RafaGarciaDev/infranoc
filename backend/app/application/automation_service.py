"""
app/application/automation_service.py

Motor de automacao: quando um alerta dispara, abre ticket no Peppermint
e (se critical) task de priorizacao no Vikunja. Quando resolve, fecha os dois.

Ajustes feitos em relacao ao documento original da Fase 6b, apos validacao manual:
1. tenant_id e recebido como PARAMETRO EXPLICITO, nao via current_tenant.get()
   (o webhook do AlertManager resolve o tenant pelo slug da URL, nao usa ContextVar).
2. Busca de ativo por Asset.name (nao Asset.hostname).
3. Contexto do ativo usa os campos reais do modelo: site, location, owner_team,
   criticality, type.
4. Fase 6b (config editavel por tenant): create_ticket e add_comment_and_close
   agora recebem session e tenant_id, pois o PeppermintClient resolve a config
   efetiva (tenant -> fallback .env) por chamada.
5. Fase 6b (auditoria): cada ticket criado/fechado no Peppermint gera uma
   entrada em AuditLog via audit_service.log(..., tenant_id=tenant_id).
"""
import uuid
import html
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.application import audit_service
from app.core.config import settings
from app.domain.models import TicketLink, Alert, Asset
from app.infrastructure.peppermint_client import PeppermintClient
from app.infrastructure.vikunja_client import VikunjaClient

SEV = {"critical": 3, "warning": 2, "high": 2, "info": 1}
peppermint = PeppermintClient()
vikunja = VikunjaClient()


def _dedup_key(alertname: str, asset: str | None) -> str:
    return f"{alertname}:{asset or 'none'}"


async def _asset_context(session: AsyncSession, tenant_id: uuid.UUID, asset_name: str | None) -> str:
    if not asset_name:
        return ""
    a = (
        await session.execute(
            select(Asset).where(Asset.tenant_id == tenant_id, Asset.name == asset_name)
        )
    ).scalar_one_or_none()
    if not a:
        return f"Ativo: {asset_name} (nao encontrado no CMDB)"
    return (
        f"Ativo: {a.display_name or a.name} ({a.type})\n"
        f"Site: {a.site} / Local: {a.location or '-'}\n"
        f"Criticidade: {a.criticality}\n"
        f"Responsavel: {a.owner_team or '-'} ({a.owner_email or '-'})"
    )


async def _is_storm(session: AsyncSession, tenant_id: uuid.UUID) -> bool:
    since = datetime.now(timezone.utc) - timedelta(seconds=settings.storm_window_seconds)
    n = (
        await session.execute(
            select(func.count()).select_from(Alert).where(
                Alert.tenant_id == tenant_id,
                Alert.starts_at >= since,
                Alert.status == "firing",
            )
        )
    ).scalar()
    return (n or 0) >= settings.storm_threshold


async def on_alert_firing(session: AsyncSession, tenant_id: uuid.UUID, alert: Alert):
    if SEV.get(alert.severity, 0) < SEV.get(settings.auto_ticket_min_severity, 2):
        return

    key = _dedup_key(alert.alertname, alert.asset)
    existing = (
        await session.execute(
            select(TicketLink).where(
                TicketLink.tenant_id == tenant_id,
                TicketLink.dedup_key == key,
                TicketLink.status == "open",
            )
        )
    ).scalar_one_or_none()
    if existing:
        return

    if await _is_storm(session, tenant_id):
        key = _dedup_key("STORM", alert.categoria)
        existing = (
            await session.execute(
                select(TicketLink).where(
                    TicketLink.tenant_id == tenant_id,
                    TicketLink.dedup_key == key,
                    TicketLink.status == "open",
                )
            )
        ).scalar_one_or_none()
        if existing:
            return

    ctx = await _asset_context(session, tenant_id, alert.asset)
    def esc(v):
        return html.escape(str(v)) if v is not None else "-"
    ctx_html = "".join(f"<p>{esc(line)}</p>" for line in (ctx or "-").split("\n"))
    detail = (
        f"<p><strong>Alerta:</strong> {esc(alert.summary)}</p>"
        f"<p><strong>Severidade:</strong> {esc(alert.severity)}</p>"
        f"<p><strong>Categoria:</strong> {esc(alert.categoria)}</p>"
        f"<p><strong>Impacto:</strong> {esc(alert.impacto_negocio or '-')}</p>"
        f"{ctx_html}"
    )
    prio_pep = {"critical": "high", "warning": "medium", "high": "medium"}.get(alert.severity, "medium")

    link = TicketLink(tenant_id=tenant_id, dedup_key=key, alert_id=alert.id, status="open")

    try:
        link.peppermint_ticket_id = await peppermint.create_ticket(
            session,
            tenant_id,
            title=f"[{alert.severity.upper()}] {alert.summary}",
            detail=detail,
            priority=prio_pep,
        )
        await audit_service.log(
            session,
            action="peppermint.ticket.create",
            target=link.peppermint_ticket_id,
            details=f"dedup_key={key} severity={alert.severity} alertname={alert.alertname}",
            tenant_id=tenant_id,
        )
    except Exception as e:
        print("Peppermint falhou:", e)

    # Vikunja fora de escopo por enquanto (decisao Fase 6b: fechar so com Peppermint).
    # Reativar removendo o comentario abaixo quando o Vikunja voltar ao escopo.
    # if SEV.get(alert.severity, 0) >= SEV.get(settings.auto_task_min_severity, 3):
    #     try:
    #         link.vikunja_task_id = await vikunja.create_task(
    #             title=f"[PRIORIZAR] {alert.summary}",
    #             description=detail,
    #             labels=["auto", "infranoc", alert.categoria or "geral"],
    #             priority=prio_vik,
    #         )
    #     except Exception as e:
    #         print("Vikunja falhou:", e)

    session.add(link)
    await session.commit()


async def on_alert_resolved(session: AsyncSession, tenant_id: uuid.UUID, alert: Alert):
    key = _dedup_key(alert.alertname, alert.asset)
    link = (
        await session.execute(
            select(TicketLink).where(
                TicketLink.tenant_id == tenant_id,
                TicketLink.dedup_key == key,
                TicketLink.status == "open",
            )
        )
    ).scalar_one_or_none()
    if not link:
        return

    if link.peppermint_ticket_id:
        try:
            await peppermint.add_comment_and_close(
                session,
                tenant_id,
                link.peppermint_ticket_id,
                f"Alerta resolvido automaticamente em {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC.",
            )
            await audit_service.log(
                session,
                action="peppermint.ticket.close",
                target=link.peppermint_ticket_id,
                details=f"dedup_key={key}",
                tenant_id=tenant_id,
            )
        except Exception as e:
            print("Peppermint fechar falhou:", e)

    # Vikunja fora de escopo por enquanto (Fase 6b fechada so com Peppermint).
    # vikunja_task_id nunca e preenchido no momento, entao este bloco fica inerte.
    if link.vikunja_task_id:
        try:
            await vikunja.mark_done(link.vikunja_task_id)
        except Exception as e:
            print("Vikunja marcar como done falhou:", e)

    link.status = "closed"
    link.closed_at = datetime.now(timezone.utc)
    await session.commit()