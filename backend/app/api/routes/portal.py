"""Portal do Usuario Final (Fase 9j).

Autenticacao via bind LDAP com a senha do proprio funcionario (nao usa a
tabela `users` do app). Chamados abertos pelo portal sao rastreados em
PortalTicket. Reset de senha self-service (sem SMTP configurado - o "envio"
retorna o link diretamente na resposta, documentado como simplificacao de
laboratorio).
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application import audit_service
from app.core.config import settings
from app.core.db import get_session
from app.core.deps import require
from app.core.security import create_portal_token
from app.domain.models import PasswordResetToken, PortalTicket
from app.infrastructure.ldap_client import LdapClient
from app.infrastructure.mock_ldap_client import MockLdapClient
from app.infrastructure.peppermint_client import PeppermintClient
from app.infrastructure.ps_ad_ops import PsAdOps

router = APIRouter(prefix="/portal", tags=["portal"])

ldap = MockLdapClient() if settings.ad_mock else LdapClient()
ps = PsAdOps()
peppermint = PeppermintClient()

_TENANT_ID = settings.ad_tenant_id
_RESET_TOKEN_TTL_MIN = 15
_RESET_MAX_PER_WINDOW = 3


class PortalLoginIn(BaseModel):
    sam: str
    password: str


class PortalLoginOut(BaseModel):
    access_token: str
    display_name: str
    email: str


@router.post("/login", response_model=PortalLoginOut)
async def portal_login(body: PortalLoginIn) -> PortalLoginOut:
    from starlette.concurrency import run_in_threadpool
    info = await run_in_threadpool(ldap.authenticate_user, body.sam, body.password)
    if info is None:
        raise HTTPException(401, "Usuario ou senha invalidos")
    token = create_portal_token(info["sam"], _TENANT_ID)
    return PortalLoginOut(access_token=token, display_name=info["display_name"], email=info["email"])


class PortalTicketCreateIn(BaseModel):
    title: str
    detail: str


class PortalTicketOut(BaseModel):
    id: str
    title: str
    detail: str
    status: str
    peppermint_ticket_id: str | None
    created_at: datetime


@router.get("/chamados", response_model=list[PortalTicketOut])
async def list_my_tickets(
    claims: Annotated[dict, Depends(require("portal.access"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[PortalTicketOut]:
    sam = claims["sub"]
    tenant_id = uuid.UUID(claims["tenant_id"])
    stmt = (
        select(PortalTicket)
        .where(PortalTicket.tenant_id == tenant_id, PortalTicket.sam == sam)
        .order_by(PortalTicket.created_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        PortalTicketOut(
            id=str(t.id), title=t.title, detail=t.detail, status=t.status,
            peppermint_ticket_id=t.peppermint_ticket_id, created_at=t.created_at,
        )
        for t in rows
    ]


@router.post("/chamados", response_model=PortalTicketOut, status_code=201)
async def create_my_ticket(
    body: PortalTicketCreateIn,
    claims: Annotated[dict, Depends(require("portal.access"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PortalTicketOut:
    sam = claims["sub"]
    tenant_id = uuid.UUID(claims["tenant_id"])
    email = f"{sam}@infranoc.lab"

    peppermint_id = None
    try:
        peppermint_id = await peppermint.create_ticket(
            session, tenant_id, title=body.title, detail=f"[Portal - {sam}]\n\n{body.detail}",
        )
    except Exception:
        pass

    ticket = PortalTicket(
        tenant_id=tenant_id, sam=sam, email=email, title=body.title, detail=body.detail,
        peppermint_ticket_id=peppermint_id, status="open",
    )
    session.add(ticket)
    await audit_service.log(session, "portal.ticket.create", target=sam, tenant_id=tenant_id)
    await session.commit()
    return PortalTicketOut(
        id=str(ticket.id), title=ticket.title, detail=ticket.detail, status=ticket.status,
        peppermint_ticket_id=ticket.peppermint_ticket_id, created_at=ticket.created_at,
    )


class ResetSolicitarIn(BaseModel):
    sam: str


class ResetSolicitarOut(BaseModel):
    reset_url: str
    aviso: str


@router.post("/reset-senha/solicitar", response_model=ResetSolicitarOut)
async def reset_solicitar(
    body: ResetSolicitarIn,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResetSolicitarOut:
    from starlette.concurrency import run_in_threadpool
    tenant_id = uuid.UUID(_TENANT_ID)

    janela = datetime.now(timezone.utc) - timedelta(minutes=_RESET_TOKEN_TTL_MIN)
    count_stmt = select(func.count()).select_from(PasswordResetToken).where(
        PasswordResetToken.sam == body.sam, PasswordResetToken.created_at >= janela,
    )
    total_recente = (await session.execute(count_stmt)).scalar_one()
    if total_recente >= _RESET_MAX_PER_WINDOW:
        raise HTTPException(429, "Muitas solicitacoes recentes; aguarde alguns minutos e tente novamente")

    users = await run_in_threadpool(ldap.search_users, body.sam, None, 5)
    if not any(u["sam"].lower() == body.sam.lower() for u in users):
        raise HTTPException(404, "Usuario nao encontrado")

    token_str = secrets.token_urlsafe(32)
    reset_token = PasswordResetToken(
        tenant_id=tenant_id, sam=body.sam, token=token_str,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=_RESET_TOKEN_TTL_MIN),
    )
    session.add(reset_token)
    await audit_service.log(session, "portal.reset_senha.solicitar", target=body.sam, tenant_id=tenant_id)
    await session.commit()

    return ResetSolicitarOut(
        reset_url=f"/portal/reset-senha/confirmar?token={token_str}",
        aviso="Ambiente de laboratorio sem SMTP configurado: em producao este link seria enviado por e-mail, nao exibido na tela.",
    )


class ResetConfirmarIn(BaseModel):
    token: str
    new_password: str


@router.post("/reset-senha/confirmar")
async def reset_confirmar(
    body: ResetConfirmarIn,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    from starlette.concurrency import run_in_threadpool
    stmt = select(PasswordResetToken).where(PasswordResetToken.token == body.token)
    reset_token = (await session.execute(stmt)).scalar_one_or_none()
    if not reset_token:
        raise HTTPException(404, "Token invalido")
    if reset_token.used:
        raise HTTPException(400, "Token ja utilizado")
    if reset_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Token expirado")

    await run_in_threadpool(ps.reset_password, reset_token.sam, body.new_password, False)
    reset_token.used = True
    await audit_service.log(
        session, "portal.reset_senha.confirmar", target=reset_token.sam, tenant_id=reset_token.tenant_id,
    )
    await session.commit()
    return {"ok": True}
