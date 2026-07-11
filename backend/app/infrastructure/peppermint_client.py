"""
app/infrastructure/peppermint_client.py
Cliente HTTP para o Peppermint v0.5.5 (help desk self-hosted).
API: REST em /api/v1 (Fastify, sem Swagger exposto).
Auth: POST /api/v1/auth/login -> JWT; renovado automaticamente.
Endpoints confirmados via inspecao do codigo-fonte (ticket.js):
  POST /api/v1/ticket/create        { title, detail, priority, email, type }
  POST /api/v1/ticket/comment       { id, text, public }
  PUT  /api/v1/ticket/status/update { id, status: bool }

Fase 6b (config editavel por tenant): a config efetiva de cada chamada
e resolvida assim, por campo:
  1) valor gravado em IntegrationSettings do tenant (se houver e nao vazio)
  2) fallback para o valor fixo em app.core.config.settings (.env)
Isso preserva o comportamento ja validado quando nenhum tenant configurou
nada pela tela /integracoes ainda.
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.models import IntegrationSettings


class PeppermintClient:
    def __init__(self):
        self._tokens: dict[str, tuple[str, datetime]] = {}
        self._lock = asyncio.Lock()

    async def _get_config_row(self, session: AsyncSession, tenant_id: uuid.UUID) -> IntegrationSettings | None:
        return (
            await session.execute(
                select(IntegrationSettings).where(IntegrationSettings.tenant_id == tenant_id)
            )
        ).scalar_one_or_none()

    @staticmethod
    def _effective(cfg: IntegrationSettings | None, field: str, fallback):
        if cfg is not None:
            val = getattr(cfg, field, None)
            if val not in (None, ""):
                return val
        return fallback

    def _resolve_from_row(self, cfg: IntegrationSettings | None) -> dict:
        return {
            "base_url": self._effective(cfg, "peppermint_url", settings.peppermint_url),
            "email": self._effective(cfg, "peppermint_email", settings.peppermint_email),
            "password": self._effective(cfg, "peppermint_password", settings.peppermint_password),
            "default_email": self._effective(cfg, "peppermint_default_email", settings.peppermint_default_email),
        }

    async def _login(self, base_url: str, email: str, password: str) -> str:
        async with httpx.AsyncClient(base_url=base_url, timeout=10) as client:
            r = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            r.raise_for_status()
            return r.json()["token"]

    async def _get_token(self, tenant_id: uuid.UUID, cfg: dict) -> str:
        key = str(tenant_id)
        async with self._lock:
            now = datetime.now(timezone.utc)
            cached = self._tokens.get(key)
            if cached is None or now >= cached[1] - timedelta(seconds=60):
                token = await self._login(cfg["base_url"], cfg["email"], cfg["password"])
                self._tokens[key] = (token, now + timedelta(hours=1))
            return self._tokens[key][0]

    def _headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def create_ticket(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        title: str,
        detail: str,
        priority: str = "medium",
    ) -> str:
        cfg_row = await self._get_config_row(session, tenant_id)
        if cfg_row is not None and not cfg_row.peppermint_enabled:
            raise RuntimeError("Peppermint desabilitado nas configuracoes deste tenant")
        cfg = self._resolve_from_row(cfg_row)
        token = await self._get_token(tenant_id, cfg)
        async with httpx.AsyncClient(base_url=cfg["base_url"], timeout=15) as client:
            r = await client.post(
                "/api/v1/ticket/create",
                headers=self._headers(token),
                json={
                    "title": title,
                    "detail": detail,
                    "priority": priority,
                    "email": cfg["default_email"],
                    "type": "support",
                },
            )
            r.raise_for_status()
            data = r.json()
            if not data.get("success") and "id" not in data:
                raise RuntimeError(f"Peppermint create_ticket falhou: {data}")
            return str(data["id"])

    async def add_comment_and_close(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        ticket_id: str,
        comment: str,
    ) -> None:
        cfg_row = await self._get_config_row(session, tenant_id)
        cfg = self._resolve_from_row(cfg_row)
        token = await self._get_token(tenant_id, cfg)
        async with httpx.AsyncClient(base_url=cfg["base_url"], timeout=15) as client:
            r = await client.post(
                "/api/v1/ticket/comment",
                headers=self._headers(token),
                json={"id": ticket_id, "text": comment, "public": False},
            )
            r.raise_for_status()
            r = await client.put(
                "/api/v1/ticket/status/update",
                headers=self._headers(token),
                json={"id": ticket_id, "status": True},
            )
            r.raise_for_status()
            data = r.json()
            if not data.get("success"):
                raise RuntimeError(f"Peppermint close falhou: {data}")