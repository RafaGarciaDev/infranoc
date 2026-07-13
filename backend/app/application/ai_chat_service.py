# app/application/ai_chat_service.py
import json
import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.application import ai_tools, audit_service
from app.application.ai_tools import TOOLS
from app.core.config import settings
from app.infrastructure import rag

SYSTEM = (
    "Voce e o assistente do InfraNOC (Laticinios Vale Verde S/A). "
    "Responda em portugues, objetivo e tecnico. Use as ferramentas para "
    "obter dados reais antes de citar numeros; nunca invente. Cite os ativos/alertas relevantes."
)


async def _run_tool(session: AsyncSession, tenant_id: uuid.UUID, name: str, args: dict):
    fn = getattr(ai_tools, name, None)
    if fn is None:
        return {"erro": f"ferramenta desconhecida: {name}"}
    try:
        return await fn(session, tenant_id, **args)
    except TypeError as e:
        return {"erro": f"argumentos invalidos para {name}: {e}"}


async def ask_stream(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    actor_email: str | None,
    question: str,
    history: list[dict],
):
    docs = await rag.search(session, rag.embed(question), top=1)
    await audit_service.log(
        session,
        action="ai.chat.question",
        details=question[:500],
        tenant_id=tenant_id,
    )

    contexto = "\n\n".join(f"## {t}\n{c}" for t, c in docs)
    system_final = SYSTEM + "\n\nDocumentos de referencia (use quando a pergunta for sobre procedimentos):\n\n" + contexto if docs else SYSTEM
    messages = (
        [{"role": "system", "content": system_final}]
        + list(history)
        + [{"role": "user", "content": question}]
    )

    async with httpx.AsyncClient(base_url=settings.ai_base_url, timeout=300.0) as client:
        for _ in range(6):
            resp = await client.post(
                "/v1/chat/completions",
                json={
                    "model": settings.ai_model,
                    "messages": messages,
                    "tools": TOOLS,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            msg = choice["message"]
            tool_calls = msg.get("tool_calls") or []

            if not tool_calls:
                text = msg.get("content") or ""
                if text:
                    yield text
                return

            messages.append(msg)

            for tc in tool_calls:
                name = tc["function"]["name"]
                raw_args = tc["function"].get("arguments") or "{}"
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                out = await _run_tool(session, tenant_id, name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": json.dumps(out, default=str, ensure_ascii=False),
                    }
                )
