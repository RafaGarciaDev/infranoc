# app/api/routes/ai.py
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai_chat_service import ask_stream
from app.core.db import get_session
from app.core.deps import require

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatReq(BaseModel):
    question: str
    history: list[dict] = []


@router.post("/chat/stream")
async def chat_stream(
    body: ChatReq,
    claims: dict = Depends(require("ai.chat")),
    session: AsyncSession = Depends(get_session),
):
    tenant_id = uuid.UUID(claims["tenant_id"])
    actor_email = claims.get("sub")

    async def gen():
        async for chunk in ask_stream(session, tenant_id, actor_email, body.question, body.history):
            yield chunk

    return StreamingResponse(gen(), media_type="text/plain")
