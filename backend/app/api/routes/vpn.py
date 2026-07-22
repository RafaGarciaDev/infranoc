"""Gestao de VPN (Fase 9i) - simulada, sem WireGuard real no lab.

Ver ADR-005 para a decisao completa. As chaves publicas e o config .conf
gerados sao fabricados (nao correspondem a um servidor WireGuard real
rodando), mas o formato e realista o suficiente para demonstrar o fluxo
completo de self-service (criar, baixar config, revogar, ver sessoes).
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application import audit_service
from app.core.db import get_session
from app.core.deps import require
from app.domain.models import VpnSession, VpnUser

router = APIRouter(prefix="/vpn", tags=["vpn"])

_STALE_THRESHOLD_MIN = 10
_SERVER_PUBLIC_KEY = "SERVER_PUBLIC_KEY_PLACEHOLDER_LAB_ONLY="
_SERVER_ENDPOINT = "vpn.valeverde.lab:51820"


def _fake_public_key() -> str:
    return secrets.token_urlsafe(32)[:43] + "="


class VpnUserOut(BaseModel):
    id: str
    name: str
    email: str
    ad_sam: str | None
    internal_ip: str
    active: bool
    expires_at: datetime | None
    last_handshake: datetime | None
    stale: bool


def _to_user_out(u: VpnUser, now: datetime) -> VpnUserOut:
    latest_session = max(u.sessions, key=lambda s: s.last_handshake) if u.sessions else None
    last_handshake = latest_session.last_handshake if latest_session else None
    stale = (
        last_handshake is not None
        and (now - last_handshake).total_seconds() > _STALE_THRESHOLD_MIN * 60
    )
    return VpnUserOut(
        id=str(u.id), name=u.name, email=u.email, ad_sam=u.ad_sam, internal_ip=u.internal_ip,
        active=u.active, expires_at=u.expires_at, last_handshake=last_handshake, stale=stale,
    )


@router.get("/users", response_model=list[VpnUserOut])
async def list_vpn_users(
    claims: Annotated[dict, Depends(require("vpn.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[VpnUserOut]:
    tenant_id = uuid.UUID(claims["tenant_id"])
    stmt = (
        select(VpnUser)
        .where(VpnUser.tenant_id == tenant_id)
        .options(selectinload(VpnUser.sessions))
        .order_by(VpnUser.name)
    )
    rows = (await session.execute(stmt)).scalars().all()
    now = datetime.now(timezone.utc)
    return [_to_user_out(u, now) for u in rows]


class VpnUserCreateIn(BaseModel):
    name: str
    email: str
    ad_sam: str | None = None
    expires_days: int = 90


@router.post("/users", response_model=VpnUserOut, status_code=201)
async def create_vpn_user(
    body: VpnUserCreateIn,
    claims: Annotated[dict, Depends(require("vpn.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VpnUserOut:
    tenant_id = uuid.UUID(claims["tenant_id"])
    existing_ips = (
        await session.execute(select(VpnUser.internal_ip).where(VpnUser.tenant_id == tenant_id))
    ).scalars().all()
    used_octets = set()
    for ip in existing_ips:
        try:
            used_octets.add(int(ip.rsplit(".", 1)[-1]))
        except ValueError:
            pass
    next_octet = 2
    while next_octet in used_octets:
        next_octet += 1

    user = VpnUser(
        tenant_id=tenant_id, name=body.name, email=body.email, ad_sam=body.ad_sam,
        public_key=_fake_public_key(), internal_ip=f"10.10.0.{next_octet}", active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=body.expires_days),
    )
    session.add(user)
    await audit_service.log(session, "vpn.user.create", target=body.email, tenant_id=tenant_id)
    await session.commit()
    await session.refresh(user, attribute_names=["sessions"])
    return _to_user_out(user, datetime.now(timezone.utc))


@router.get("/users/{user_id}/config")
async def download_vpn_config(
    user_id: str,
    claims: Annotated[dict, Depends(require("vpn.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    tenant_id = uuid.UUID(claims["tenant_id"])
    user = await session.get(VpnUser, uuid.UUID(user_id))
    if not user or user.tenant_id != tenant_id:
        raise HTTPException(404, "Usuario VPN nao encontrado")

    config = (
        f"[Interface]\n"
        f"PrivateKey = CLIENT_PRIVATE_KEY_GERAR_LOCALMENTE\n"
        f"Address = {user.internal_ip}/24\n"
        f"DNS = 10.10.0.1\n\n"
        f"[Peer]\n"
        f"PublicKey = {_SERVER_PUBLIC_KEY}\n"
        f"Endpoint = {_SERVER_ENDPOINT}\n"
        f"AllowedIPs = 10.10.0.0/24, 192.168.56.0/24\n"
        f"PersistentKeepalive = 25\n"
    )
    await audit_service.log(session, "vpn.user.download_config", target=user.email, tenant_id=tenant_id)
    filename = user.email.split("@")[0]
    return Response(
        content=config, media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}.conf"'},
    )


@router.delete("/users/{user_id}")
async def revoke_vpn_user(
    user_id: str,
    claims: Annotated[dict, Depends(require("vpn.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    tenant_id = uuid.UUID(claims["tenant_id"])
    user = await session.get(VpnUser, uuid.UUID(user_id))
    if not user or user.tenant_id != tenant_id:
        raise HTTPException(404, "Usuario VPN nao encontrado")
    user.active = False
    await audit_service.log(session, "vpn.user.revoke", target=user.email, tenant_id=tenant_id)
    await session.commit()
    return {"ok": True}


@router.post("/users/{user_id}/reactivate", response_model=VpnUserOut)
async def reactivate_vpn_user(
    user_id: str,
    claims: Annotated[dict, Depends(require("vpn.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VpnUserOut:
    tenant_id = uuid.UUID(claims["tenant_id"])
    user = await session.get(VpnUser, uuid.UUID(user_id))
    if not user or user.tenant_id != tenant_id:
        raise HTTPException(404, "Usuario VPN nao encontrado")
    user.active = True
    user.expires_at = datetime.now(timezone.utc) + timedelta(days=90)
    await audit_service.log(session, "vpn.user.reactivate", target=user.email, tenant_id=tenant_id)
    await session.commit()
    await session.refresh(user, attribute_names=["sessions"])
    return _to_user_out(user, datetime.now(timezone.utc))


class VpnUserUpdateIn(BaseModel):
    name: str | None = None
    email: str | None = None
    ad_sam: str | None = None
    expires_at: datetime | None = None


@router.patch("/users/{user_id}", response_model=VpnUserOut)
async def update_vpn_user(
    user_id: str,
    body: VpnUserUpdateIn,
    claims: Annotated[dict, Depends(require("vpn.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VpnUserOut:
    tenant_id = uuid.UUID(claims["tenant_id"])
    user = await session.get(VpnUser, uuid.UUID(user_id))
    if not user or user.tenant_id != tenant_id:
        raise HTTPException(404, "Usuario VPN nao encontrado")
    if body.name is not None:
        user.name = body.name
    if body.email is not None:
        user.email = body.email
    if body.ad_sam is not None:
        user.ad_sam = body.ad_sam
    if body.expires_at is not None:
        user.expires_at = body.expires_at
    await audit_service.log(session, "vpn.user.update", target=user.email, tenant_id=tenant_id)
    await session.commit()
    await session.refresh(user, attribute_names=["sessions"])
    return _to_user_out(user, datetime.now(timezone.utc))


@router.post("/users/{user_id}/simulate-handshake", response_model=VpnUserOut)
async def simulate_handshake(
    user_id: str,
    claims: Annotated[dict, Depends(require("vpn.write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VpnUserOut:
    tenant_id = uuid.UUID(claims["tenant_id"])
    result = await session.execute(
        select(VpnUser).options(selectinload(VpnUser.sessions)).where(VpnUser.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()
    if not user or user.tenant_id != tenant_id:
        raise HTTPException(404, "Usuario VPN nao encontrado")
    now = datetime.now(timezone.utc)
    if user.sessions:
        latest = max(user.sessions, key=lambda s: s.last_handshake)
        latest.last_handshake = now
    else:
        session.add(VpnSession(
            vpn_user_id=user.id,
            endpoint_publico=f"{user.internal_ip}:51820",
            connected_at=now,
            last_handshake=now,
            bytes_rx=0,
            bytes_tx=0,
        ))
    await audit_service.log(session, "vpn.user.simulate_handshake", target=user.email, tenant_id=tenant_id)
    await session.commit()
    await session.refresh(user, attribute_names=["sessions"])
    return _to_user_out(user, datetime.now(timezone.utc))


class VpnSessionOut(BaseModel):
    user_name: str
    user_email: str
    endpoint_publico: str
    connected_at: datetime
    last_handshake: datetime
    bytes_rx: int
    bytes_tx: int
    stale: bool


@router.get("/sessions", response_model=list[VpnSessionOut])
async def list_vpn_sessions(
    claims: Annotated[dict, Depends(require("vpn.read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[VpnSessionOut]:
    tenant_id = uuid.UUID(claims["tenant_id"])
    stmt = (
        select(VpnSession)
        .join(VpnUser, VpnUser.id == VpnSession.vpn_user_id)
        .where(VpnUser.tenant_id == tenant_id, VpnUser.active.is_(True))
        .options(selectinload(VpnSession.vpn_user))
        .order_by(VpnSession.last_handshake.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    now = datetime.now(timezone.utc)
    return [
        VpnSessionOut(
            user_name=s.vpn_user.name, user_email=s.vpn_user.email,
            endpoint_publico=s.endpoint_publico, connected_at=s.connected_at,
            last_handshake=s.last_handshake, bytes_rx=s.bytes_rx, bytes_tx=s.bytes_tx,
            stale=(now - s.last_handshake).total_seconds() > _STALE_THRESHOLD_MIN * 60,
        )
        for s in rows
    ]
