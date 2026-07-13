"""Job de reindexacao do RAG.

Le os runbooks em docs/runbooks/, gera embeddings locais
(embed_passage) e regrava na tabela knowledge_docs.
O job usa SessionLocal diretamente (fora de request FastAPI),
no mesmo padrao do ad_audit_job.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from sqlalchemy import delete

from app.core.config import settings
from app.core.db import SessionLocal
from app.domain.models import KnowledgeDoc
from app.infrastructure.rag import embed_passage

logger = logging.getLogger(__name__)

RUNBOOKS_DIR = Path(__file__).resolve().parents[2] / "docs" / "runbooks"


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


async def reindex_runbooks() -> None:
    if not RUNBOOKS_DIR.is_dir():
        logger.warning("rag_reindex_job: diretorio %s nao existe", RUNBOOKS_DIR)
        return

    files = sorted(RUNBOOKS_DIR.glob("*.md"))
    if not files:
        logger.info("rag_reindex_job: nenhum runbook encontrado")
        return

    tenant_id = uuid.UUID(settings.ad_tenant_id)
    docs: list[KnowledgeDoc] = []
    for path in files:
        content = path.read_text(encoding="utf-8-sig")
        title = _extract_title(content, path.stem)
        docs.append(KnowledgeDoc(
            tenant_id=tenant_id,
            source_type="runbook",
            source_ref=path.name,
            title=title,
            content=content,
            embedding=embed_passage(content),
        ))

    async with SessionLocal() as session:
        await session.execute(
            delete(KnowledgeDoc).where(
                KnowledgeDoc.tenant_id == tenant_id,
                KnowledgeDoc.source_type == "runbook",
            )
        )
        session.add_all(docs)
        await session.commit()

    logger.info("rag_reindex_job: %d runbooks reindexados", len(docs))
