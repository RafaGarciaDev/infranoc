"""Active Directory - modulo de gerenciamento de usuarios do dominio (Fase 5).

Endpoints REST para listar, criar, resetar senha, desbloquear, habilitar/
desabilitar e gerenciar grupos dos ~250 usuarios do dominio infranoc.lab,
alem de expor o historico de auditoria de eventos coletados da DC.

Todas as chamadas a ldap3/pypsrp sao bloqueantes (I/O de rede sincrono),
entao rodam em threadpool (run_in_threadpool) para nao travar o event loop
do FastAPI enquanto esperam a DC responder.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.application import audit_service
from app.core.db import get_session
from app.core.deps import require
from app.domain.models import AdAuditEvent
from app.core.config import settings
from app.infrastructure.ldap_client import LdapClient
from app.infrastructure.mock_ldap_client import MockLdapClient
from app.infrastructure.ps_ad_ops import PsAdOps

router = APIRouter(prefix="/directory", tags=["active-directory"])

# Um unico cliente por processo: ldap3.Server/Connection e pypsrp.Client
# abrem a conexao sob demanda a cada operacao, entao nao ha estado
# compartilhado perigoso em manter uma instancia so.
ldap = MockLdapClient() if settings.ad_mock else LdapClient()
ps = PsAdOps()


# ------------------------------------------------------------------
# Schemas de resposta
# ------------------------------------------------------------------
class ADUserOut(BaseModel):
    sam: str
    display_name: str
    email: str
    title: str
    department: str
    disabled: bool
    locked: bool
    dn: str
    groups: list[str]


class ADSummaryOut(BaseModel):
    total: int
    locked: int
    disabled: int
    by_department: dict[str, int]


class ADAuditEventOut(BaseModel):
    id: uuid.UUID
    event_id: int
    at: datetime
    target_sam: str | None
    actor_sam: str | None
    message: str

    model_config = {"from_attributes": True}


class ResetPasswordIn(BaseModel):
    new_password: str
    must_change: bool = True


class GroupChangeIn(BaseModel):
    group_dn: str
    add: bool = True


def _count_by(rows: list[dict], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        out[r[key]] = out.get(r[key], 0) + 1
    return out


# ------------------------------------------------------------------
# Leitura
# ------------------------------------------------------------------
@router.get("/users", response_model=list[ADUserOut])
async def list_users(
    claims: Annotated[dict, Depends(require("ad.read"))],
    q: str | None = None,
    ou: str | None = None,
) -> list[ADUserOut]:
    rows = await run_in_threadpool(ldap.search_users, q, ou)
    return [ADUserOut(**r) for r in rows]


@router.get("/summary", response_model=ADSummaryOut)
async def summary(
    claims: Annotated[dict, Depends(require("ad.read"))],
) -> ADSummaryOut:
    rows = await run_in_threadpool(ldap.search_users, None, None, 1000)
    return ADSummaryOut(
        total=len(rows),
        locked=sum(1 for u in rows if u["locked"]),
        disabled=sum(1 for u in rows if u["disabled"]),
        by_department=_count_by(rows, "department"),
    )


# ------------------------------------------------------------------
# Escrita (LDAP: enable/disable, grupos)
# ------------------------------------------------------------------
@router.post("/users/{sam}/enable")
async def set_enabled(
    sam: str,
    claims: Annotated[dict, Depends(require("ad.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    value: bool = True,
) -> dict:
    await run_in_threadpool(ldap.set_enabled, sam, value)
    await audit_service.log(
        session, "ad.user.enable" if value else "ad.user.disable", target=sam
    )
    return {"ok": True}


@router.post("/users/{sam}/groups")
async def change_group(
    sam: str,
    body: GroupChangeIn,
    claims: Annotated[dict, Depends(require("ad.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    await run_in_threadpool(ldap.set_group, sam, body.group_dn, body.add)
    await audit_service.log(
        session,
        "ad.group.add" if body.add else "ad.group.remove",
        target=f"{sam}->{body.group_dn}",
    )
    return {"ok": True}


# ------------------------------------------------------------------
# Escrita (PowerShell: reset de senha, unlock)
# ------------------------------------------------------------------
@router.post("/users/{sam}/reset-password")
async def reset_password(
    sam: str,
    body: ResetPasswordIn,
    claims: Annotated[dict, Depends(require("ad.reset-password"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    await run_in_threadpool(ps.reset_password, sam, body.new_password, body.must_change)
    # Nunca gravar a nova senha no audit_log — so o sam do alvo.
    await audit_service.log(session, "ad.user.reset-password", target=sam)
    return {"ok": True}


@router.post("/users/{sam}/unlock")
async def unlock(
    sam: str,
    claims: Annotated[dict, Depends(require("ad.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    await run_in_threadpool(ps.unlock, sam)
    await audit_service.log(session, "ad.user.unlock", target=sam)
    return {"ok": True}


# ------------------------------------------------------------------
# Auditoria (eventos coletados da DC pelo job APScheduler - Bloco 6)
# ------------------------------------------------------------------
@router.get("/audit", response_model=list[ADAuditEventOut])
async def list_audit(
    claims: Annotated[dict, Depends(require("audit.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    event_id: int | None = None,
    target_sam: str | None = None,
    limit: int = 100,
) -> list[ADAuditEventOut]:
    tenant_id = uuid.UUID(claims["tenant_id"])
    stmt = (
        select(AdAuditEvent)
        .where(AdAuditEvent.tenant_id == tenant_id)
        .order_by(AdAuditEvent.at.desc())
        .limit(limit)
    )
    if event_id is not None:
        stmt = stmt.where(AdAuditEvent.event_id == event_id)
    if target_sam is not None:
        stmt = stmt.where(AdAuditEvent.target_sam == target_sam)

    rows = (await session.execute(stmt)).scalars().all()
    return [ADAuditEventOut.model_validate(r) for r in rows]


# ------------------------------------------------------------------
# Fase 9c - Gestao de OUs (Organizational Units)
# ------------------------------------------------------------------
class OUOut(BaseModel):
    name: str
    dn: str
    parent_dn: str


class OUCreateIn(BaseModel):
    name: str
    parent_dn: str | None = None


class OURenameIn(BaseModel):
    dn: str
    new_name: str


class OUMoveIn(BaseModel):
    dn: str
    new_parent_dn: str


class OUDeleteIn(BaseModel):
    dn: str


@router.get("/ous", response_model=list[OUOut])
async def list_ous_route(
    claims: Annotated[dict, Depends(require("ad.read"))],
    base_dn: str | None = None,
) -> list[OUOut]:
    rows = await run_in_threadpool(ldap.list_ous, base_dn)
    return [OUOut(**r) for r in rows]


@router.post("/ous")
async def create_ou_route(
    body: OUCreateIn,
    claims: Annotated[dict, Depends(require("ad.ou.manage"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    dn = await run_in_threadpool(ldap.create_ou, body.name, body.parent_dn)
    await audit_service.log(session, "ad.ou.create", target=dn)
    return {"dn": dn}


@router.post("/ous/rename")
async def rename_ou_route(
    body: OURenameIn,
    claims: Annotated[dict, Depends(require("ad.ou.manage"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    new_dn = await run_in_threadpool(ldap.rename_ou, body.dn, body.new_name)
    await audit_service.log(session, "ad.ou.rename", target=f"{body.dn}->{new_dn}")
    return {"dn": new_dn}


@router.post("/ous/move")
async def move_ou_route(
    body: OUMoveIn,
    claims: Annotated[dict, Depends(require("ad.ou.manage"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    new_dn = await run_in_threadpool(ldap.move_ou, body.dn, body.new_parent_dn)
    await audit_service.log(session, "ad.ou.move", target=f"{body.dn}->{new_dn}")
    return {"dn": new_dn}


@router.post("/ous/delete")
async def delete_ou_route(
    body: OUDeleteIn,
    claims: Annotated[dict, Depends(require("ad.ou.manage"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    try:
        await run_in_threadpool(ldap.delete_ou, body.dn)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(400, str(e))
    await audit_service.log(session, "ad.ou.delete", target=body.dn)
    return {"ok": True}
