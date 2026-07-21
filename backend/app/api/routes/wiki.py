"""Rotas da Base de Conhecimento (Wiki interna) - Fase 9b.

CRUD de paginas markdown, com historico de versoes e integracao direta
com o RAG: toda vez que uma pagina e criada/editada, o embedding e
gerado e a linha correspondente em knowledge_docs e atualizada (upsert),
para que o chat de IA (Fase 7) passe a usa-la automaticamente na
proxima pergunta (rag.search le knowledge_docs sem filtrar por
source_type).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.application import audit_service
from app.core.db import get_session
from app.core.deps import require
from app.domain.models import KnowledgeDoc, WikiPage, WikiPageVersion
from app.infrastructure.rag import embed_passage

router = APIRouter(prefix="/wiki", tags=["wiki"])

_CATEGORIAS_VALIDAS = {"rede", "ad", "linux", "ot", "energia", "seguranca", "geral"}


class WikiPageListItem(BaseModel):
    slug: str
    title: str
    category: str
    tags: list[str]
    version: int
    updated_at: datetime


class WikiPageDetail(WikiPageListItem):
    content_md: str
    author_email: str | None


class WikiPageCreate(BaseModel):
    slug: str
    title: str
    category: str
    content_md: str
    tags: list[str] = []


class WikiPageUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    content_md: str | None = None
    tags: list[str] | None = None


class WikiPageVersionOut(BaseModel):
    version: int
    author_email: str | None
    created_at: datetime


async def _reindex_page(session: AsyncSession, tenant_id: uuid.UUID, page: WikiPage) -> None:
    """Upsert do embedding da pagina na tabela knowledge_docs (source_type=wiki_page)."""
    embedding = await run_in_threadpool(embed_passage, f"{page.title}\n\n{page.content_md}")
    source_ref = page.slug
    existing = (
        await session.execute(
            select(KnowledgeDoc).where(
                KnowledgeDoc.tenant_id == tenant_id,
                KnowledgeDoc.source_type == "wiki_page",
                KnowledgeDoc.source_ref == source_ref,
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.title = page.title
        existing.content = page.content_md
        existing.embedding = embedding
    else:
        session.add(
            KnowledgeDoc(
                tenant_id=tenant_id,
                source_type="wiki_page",
                source_ref=source_ref,
                title=page.title,
                content=page.content_md,
                embedding=embedding,
            )
        )


@router.get("", response_model=list[WikiPageListItem])
async def list_pages(
    category: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    claims: dict = Depends(require("wiki.read")),
    session: AsyncSession = Depends(get_session),
) -> list[WikiPageListItem]:
    tenant_id = uuid.UUID(claims["tenant_id"])
    q = select(WikiPage).where(WikiPage.tenant_id == tenant_id).order_by(WikiPage.updated_at.desc())
    if category:
        q = q.where(WikiPage.category == category)
    rows = (await session.execute(q)).scalars().all()
    if tag:
        rows = [r for r in rows if tag in (r.tags or [])]
    return [
        WikiPageListItem(
            slug=r.slug, title=r.title, category=r.category,
            tags=r.tags or [], version=r.version, updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.get("/{slug}", response_model=WikiPageDetail)
async def get_page(
    slug: str,
    claims: dict = Depends(require("wiki.read")),
    session: AsyncSession = Depends(get_session),
) -> WikiPageDetail:
    tenant_id = uuid.UUID(claims["tenant_id"])
    page = (
        await session.execute(
            select(WikiPage).where(WikiPage.tenant_id == tenant_id, WikiPage.slug == slug)
        )
    ).scalar_one_or_none()
    if not page:
        raise HTTPException(404, f"Pagina '{slug}' nao encontrada")
    return WikiPageDetail(
        slug=page.slug, title=page.title, category=page.category,
        tags=page.tags or [], version=page.version, updated_at=page.updated_at,
        content_md=page.content_md, author_email=page.author_email,
    )


@router.get("/{slug}/history", response_model=list[WikiPageVersionOut])
async def get_history(
    slug: str,
    claims: dict = Depends(require("wiki.read")),
    session: AsyncSession = Depends(get_session),
) -> list[WikiPageVersionOut]:
    tenant_id = uuid.UUID(claims["tenant_id"])
    page = (
        await session.execute(
            select(WikiPage).where(WikiPage.tenant_id == tenant_id, WikiPage.slug == slug)
        )
    ).scalar_one_or_none()
    if not page:
        raise HTTPException(404, f"Pagina '{slug}' nao encontrada")
    versions = (
        await session.execute(
            select(WikiPageVersion)
            .where(WikiPageVersion.page_id == page.id)
            .order_by(WikiPageVersion.version.desc())
        )
    ).scalars().all()
    return [
        WikiPageVersionOut(version=v.version, author_email=v.author_email, created_at=v.created_at)
        for v in versions
    ]


@router.post("", response_model=WikiPageDetail, status_code=201)
async def create_page(
    body: WikiPageCreate,
    claims: dict = Depends(require("wiki.write")),
    session: AsyncSession = Depends(get_session),
) -> WikiPageDetail:
    tenant_id = uuid.UUID(claims["tenant_id"])
    if body.category not in _CATEGORIAS_VALIDAS:
        raise HTTPException(400, f"categoria invalida; use uma de {sorted(_CATEGORIAS_VALIDAS)}")
    existing = (
        await session.execute(
            select(WikiPage).where(WikiPage.tenant_id == tenant_id, WikiPage.slug == body.slug)
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"ja existe uma pagina com slug '{body.slug}'")

    actor = claims.get("email") or claims.get("sub")
    page = WikiPage(
        tenant_id=tenant_id, slug=body.slug, title=body.title, category=body.category,
        content_md=body.content_md, tags=body.tags, author_email=actor, version=1,
    )
    session.add(page)
    await session.flush()

    session.add(
        WikiPageVersion(
            page_id=page.id, version=1, content_md=body.content_md, author_email=actor,
        )
    )
    await _reindex_page(session, tenant_id, page)
    await audit_service.log(session, "wiki.page.create", target=page.slug, tenant_id=tenant_id)
    await session.commit()

    return WikiPageDetail(
        slug=page.slug, title=page.title, category=page.category,
        tags=page.tags or [], version=page.version, updated_at=page.updated_at,
        content_md=page.content_md, author_email=page.author_email,
    )


@router.put("/{slug}", response_model=WikiPageDetail)
async def update_page(
    slug: str,
    body: WikiPageUpdate,
    claims: dict = Depends(require("wiki.write")),
    session: AsyncSession = Depends(get_session),
) -> WikiPageDetail:
    tenant_id = uuid.UUID(claims["tenant_id"])
    page = (
        await session.execute(
            select(WikiPage).where(WikiPage.tenant_id == tenant_id, WikiPage.slug == slug)
        )
    ).scalar_one_or_none()
    if not page:
        raise HTTPException(404, f"Pagina '{slug}' nao encontrada")
    if body.category is not None and body.category not in _CATEGORIAS_VALIDAS:
        raise HTTPException(400, f"categoria invalida; use uma de {sorted(_CATEGORIAS_VALIDAS)}")

    actor = claims.get("email") or claims.get("sub")
    if body.title is not None:
        page.title = body.title
    if body.category is not None:
        page.category = body.category
    if body.tags is not None:
        page.tags = body.tags
    if body.content_md is not None:
        page.content_md = body.content_md
        page.version += 1
        session.add(
            WikiPageVersion(
                page_id=page.id, version=page.version, content_md=body.content_md, author_email=actor,
            )
        )

    await _reindex_page(session, tenant_id, page)
    await audit_service.log(session, "wiki.page.update", target=page.slug, tenant_id=tenant_id)
    await session.commit()

    return WikiPageDetail(
        slug=page.slug, title=page.title, category=page.category,
        tags=page.tags or [], version=page.version, updated_at=page.updated_at,
        content_md=page.content_md, author_email=page.author_email,
    )


@router.delete("/{slug}", status_code=204)
async def delete_page(
    slug: str,
    claims: dict = Depends(require("wiki.write")),
    session: AsyncSession = Depends(get_session),
) -> None:
    tenant_id = uuid.UUID(claims["tenant_id"])
    page = (
        await session.execute(
            select(WikiPage).where(WikiPage.tenant_id == tenant_id, WikiPage.slug == slug)
        )
    ).scalar_one_or_none()
    if not page:
        raise HTTPException(404, f"Pagina '{slug}' nao encontrada")
    await session.execute(
        delete(KnowledgeDoc).where(
            KnowledgeDoc.tenant_id == tenant_id,
            KnowledgeDoc.source_type == "wiki_page",
            KnowledgeDoc.source_ref == page.slug,
        )
    )
    await audit_service.log(session, "wiki.page.delete", target=page.slug, tenant_id=tenant_id)
    await session.delete(page)
    await session.commit()
