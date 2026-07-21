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
    last_logon: str | None = None


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


# ------------------------------------------------------------------
# Fase 9c - Gestao de Grupos
# ------------------------------------------------------------------
class GroupOut(BaseModel):
    name: str
    dn: str
    description: str
    scope: str
    group_type: str
    member_count: int


class GroupCreateIn(BaseModel):
    name: str
    parent_dn: str | None = None
    scope: str = "Global"
    group_type: str = "Security"
    description: str = ""


class GroupRenameIn(BaseModel):
    dn: str
    new_name: str


class GroupUpdateIn(BaseModel):
    dn: str
    description: str | None = None
    scope: str | None = None
    group_type: str | None = None


class GroupDeleteIn(BaseModel):
    dn: str


@router.get("/groups", response_model=list[GroupOut])
async def list_groups_route(
    claims: Annotated[dict, Depends(require("ad.read"))],
    base_dn: str | None = None,
) -> list[GroupOut]:
    rows = await run_in_threadpool(ldap.list_groups, base_dn)
    return [GroupOut(**r) for r in rows]


@router.post("/groups")
async def create_group_route(
    body: GroupCreateIn,
    claims: Annotated[dict, Depends(require("ad.group.manage"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    try:
        dn = await run_in_threadpool(
            ldap.create_group, body.name, body.parent_dn, body.scope, body.group_type, body.description
        )
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(400, str(e))
    await audit_service.log(session, "ad.group.create", target=dn)
    return {"dn": dn}


@router.post("/groups/rename")
async def rename_group_route(
    body: GroupRenameIn,
    claims: Annotated[dict, Depends(require("ad.group.manage"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    new_dn = await run_in_threadpool(ldap.rename_group, body.dn, body.new_name)
    await audit_service.log(session, "ad.group.rename", target=f"{body.dn}->{new_dn}")
    return {"dn": new_dn}


@router.post("/groups/update")
async def update_group_route(
    body: GroupUpdateIn,
    claims: Annotated[dict, Depends(require("ad.group.manage"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    try:
        await run_in_threadpool(ldap.update_group, body.dn, body.description, body.scope, body.group_type)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(400, str(e))
    await audit_service.log(session, "ad.group.update", target=body.dn)
    return {"ok": True}


@router.post("/groups/delete")
async def delete_group_route(
    body: GroupDeleteIn,
    claims: Annotated[dict, Depends(require("ad.group.manage"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    await run_in_threadpool(ldap.delete_group, body.dn)
    await audit_service.log(session, "ad.group.delete", target=body.dn)
    return {"ok": True}


# ------------------------------------------------------------------
# Fase 9c - Gestao de Computadores
# ------------------------------------------------------------------
class ComputerOut(BaseModel):
    name: str
    dn: str
    os: str
    disabled: bool


class ComputerEnableIn(BaseModel):
    dn: str
    value: bool = True


class ComputerMoveIn(BaseModel):
    dn: str
    new_parent_dn: str


class ComputerDeleteIn(BaseModel):
    dn: str


@router.get("/computers", response_model=list[ComputerOut])
async def list_computers_route(
    claims: Annotated[dict, Depends(require("ad.read"))],
    base_dn: str | None = None,
) -> list[ComputerOut]:
    rows = await run_in_threadpool(ldap.list_computers, base_dn)
    return [ComputerOut(**r) for r in rows]


@router.post("/computers/enable")
async def set_computer_enabled_route(
    body: ComputerEnableIn,
    claims: Annotated[dict, Depends(require("ad.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    await run_in_threadpool(ldap.set_computer_enabled, body.dn, body.value)
    await audit_service.log(
        session, "ad.computer.enable" if body.value else "ad.computer.disable", target=body.dn
    )
    return {"ok": True}


@router.post("/computers/move")
async def move_computer_route(
    body: ComputerMoveIn,
    claims: Annotated[dict, Depends(require("ad.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    new_dn = await run_in_threadpool(ldap.move_computer, body.dn, body.new_parent_dn)
    await audit_service.log(session, "ad.computer.move", target=f"{body.dn}->{new_dn}")
    return {"dn": new_dn}


@router.post("/computers/delete")
async def delete_computer_route(
    body: ComputerDeleteIn,
    claims: Annotated[dict, Depends(require("ad.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    await run_in_threadpool(ldap.delete_computer, body.dn)
    await audit_service.log(session, "ad.computer.delete", target=body.dn)
    return {"ok": True}


# ------------------------------------------------------------------
# Fase 9c - Membros de grupo (diretos vs herdados)
# ------------------------------------------------------------------
class GroupMemberOut(BaseModel):
    dn: str
    name: str
    sam: str | None
    direct: bool
    via: list[str]


@router.get("/groups/members", response_model=list[GroupMemberOut])
async def list_group_members_route(
    claims: Annotated[dict, Depends(require("ad.read"))],
    group_dn: str,
) -> list[GroupMemberOut]:
    rows = await run_in_threadpool(ldap.list_group_members, group_dn)
    return [GroupMemberOut(**r) for r in rows]


# ------------------------------------------------------------------
# Fase 9c - GPOs (leitura)
# ------------------------------------------------------------------
class GPOOut(BaseModel):
    name: str | None
    id: str | None
    status: str | None
    created: str | None
    modified: str | None


@router.get("/gpos", response_model=list[GPOOut])
async def list_gpos_route(
    claims: Annotated[dict, Depends(require("ad.read"))],
) -> list[GPOOut]:
    rows = await run_in_threadpool(ps.list_gpos)
    return [GPOOut(**r) for r in rows]


# ------------------------------------------------------------------
# Fase 9c - Sessoes RDP ativas
# ------------------------------------------------------------------
class RdpSessionOut(BaseModel):
    username: str
    session_name: str
    state: str
    idle_time: str
    logon_time: str


@router.get("/rdp-sessions", response_model=list[RdpSessionOut])
async def list_rdp_sessions_route(
    claims: Annotated[dict, Depends(require("ad.read"))],
) -> list[RdpSessionOut]:
    rows = await run_in_threadpool(ps.list_rdp_sessions)
    return [RdpSessionOut(**r) for r in rows]


# ------------------------------------------------------------------
# Fase 9c - Bulk operations + reset de senha em massa
# ------------------------------------------------------------------
class BulkResultItem(BaseModel):
    sam: str
    ok: bool
    error: str | None = None


class BulkEnableIn(BaseModel):
    sams: list[str]
    value: bool = True


class BulkGroupIn(BaseModel):
    sams: list[str]
    group_dn: str
    add: bool = True


class BulkResetPasswordIn(BaseModel):
    sams: list[str]
    new_password: str
    must_change: bool = True


@router.post("/bulk/enable", response_model=list[BulkResultItem])
async def bulk_enable_route(
    body: BulkEnableIn,
    claims: Annotated[dict, Depends(require("ad.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[BulkResultItem]:
    results: list[BulkResultItem] = []
    for sam in body.sams:
        try:
            await run_in_threadpool(ldap.set_enabled, sam, body.value)
            results.append(BulkResultItem(sam=sam, ok=True))
        except Exception as e:
            results.append(BulkResultItem(sam=sam, ok=False, error=str(e)))
    await audit_service.log(
        session,
        "ad.bulk.enable" if body.value else "ad.bulk.disable",
        target=",".join(body.sams),
    )
    return results


@router.post("/bulk/group", response_model=list[BulkResultItem])
async def bulk_group_route(
    body: BulkGroupIn,
    claims: Annotated[dict, Depends(require("ad.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[BulkResultItem]:
    results: list[BulkResultItem] = []
    for sam in body.sams:
        try:
            await run_in_threadpool(ldap.set_group, sam, body.group_dn, body.add)
            results.append(BulkResultItem(sam=sam, ok=True))
        except Exception as e:
            results.append(BulkResultItem(sam=sam, ok=False, error=str(e)))
    await audit_service.log(
        session,
        "ad.bulk.group_add" if body.add else "ad.bulk.group_remove",
        target=f"{','.join(body.sams)} -> {body.group_dn}",
    )
    return results


@router.post("/bulk/reset-password", response_model=list[BulkResultItem])
async def bulk_reset_password_route(
    body: BulkResetPasswordIn,
    claims: Annotated[dict, Depends(require("ad.reset-password"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[BulkResultItem]:
    results: list[BulkResultItem] = []
    for sam in body.sams:
        try:
            await run_in_threadpool(ps.reset_password, sam, body.new_password, body.must_change)
            results.append(BulkResultItem(sam=sam, ok=True))
        except Exception as e:
            results.append(BulkResultItem(sam=sam, ok=False, error=str(e)))
    await audit_service.log(session, "ad.bulk.reset-password", target=",".join(body.sams))
    return results


from fastapi import File, HTTPException, UploadFile
from fastapi.responses import Response


# ------------------------------------------------------------------
# Fase 9c - Foto do usuario
# ------------------------------------------------------------------
@router.get("/users/{sam}/photo")
async def get_user_photo_route(
    sam: str,
    claims: Annotated[dict, Depends(require("ad.read"))],
):
    photo = await run_in_threadpool(ldap.get_user_photo, sam)
    if photo is None:
        raise HTTPException(404, "Usuario sem foto cadastrada")
    return Response(content=photo, media_type="image/jpeg")


@router.post("/users/{sam}/photo")
async def upload_user_photo_route(
    sam: str,
    claims: Annotated[dict, Depends(require("ad.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    file: UploadFile = File(...),
):
    data = await file.read()
    if len(data) > 100 * 1024:
        raise HTTPException(400, "Foto muito grande (maximo 100KB)")
    await run_in_threadpool(ldap.set_user_photo, sam, data)
    await audit_service.log(session, "ad.user.photo_upload", target=sam)
    return {"ok": True}
