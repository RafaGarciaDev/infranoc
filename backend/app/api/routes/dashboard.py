"""Rotas do Dashboard NOC (Fase 6).

Expoe:
  GET  /dashboard/overview  - payload agregado (OEE, ativos, alertas, producao)
  GET  /dashboard/plant     - severidade por area do mapa
  WS   /dashboard/ws        - push do payload combinado a cada 5s

O WebSocket valida o token via query string antes de aceitar a conexao
(nao ha middleware de auth pra ws://). O tenant vem das claims do JWT.
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dashboard_service import overview, plant_status
from app.core.db import SessionLocal, get_session
from app.core.deps import require
from app.core.security import decode_token

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)

WS_PUSH_INTERVAL_SECONDS = 5


@router.get("/overview")
async def get_overview(
    claims: dict = Depends(require("alerts.read")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    tenant_id = uuid.UUID(claims["tenant_id"])
    return await overview(session, tenant_id)


@router.get("/plant")
async def get_plant(
    claims: dict = Depends(require("alerts.read")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    tenant_id = uuid.UUID(claims["tenant_id"])
    return await plant_status(session, tenant_id)


@router.websocket("/ws")
async def ws_dashboard(websocket: WebSocket) -> None:
    """Stream do payload combinado (overview + plant) a cada 5s.

    Auth via query string: ws://.../dashboard/ws?token=<jwt>
    Fecha com 1008 (policy violation) se o token for invalido ou faltar
    a permissao alerts.read.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        claims = decode_token(token)
        if claims.get("type") != "access":
            raise ValueError("token nao e do tipo access")
        if "alerts.read" not in set(claims.get("perm", [])):
            raise PermissionError("sem permissao alerts.read")
        tenant_id = uuid.UUID(claims["tenant_id"])
    except Exception as exc:
        logger.info("ws recusado: %s", exc)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    try:
        while True:
            async with SessionLocal() as session:
                payload = await overview(session, tenant_id)
                payload["plant"] = (await plant_status(session, tenant_id))["areas"]
            await websocket.send_json(payload)
            await asyncio.sleep(WS_PUSH_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        return
    except Exception:
        logger.exception("erro no loop do ws /dashboard/ws")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass