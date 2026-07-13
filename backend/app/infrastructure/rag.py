# app/infrastructure/rag.py
from functools import lru_cache

from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed(text_in: str) -> list[float]:
    model = _get_model()
    vec = model.encode(f"query: {text_in}", normalize_embeddings=True)
    return vec.tolist()


def embed_passage(text_in: str) -> list[float]:
    model = _get_model()
    vec = model.encode(f"passage: {text_in}", normalize_embeddings=True)
    return vec.tolist()


async def search(session: AsyncSession, query_embedding: list[float], top: int = 4):
    rows = await session.execute(
        text(
            "SELECT title, content FROM knowledge_docs "
            "ORDER BY embedding <=> CAST(:emb AS vector) LIMIT :top"
        ),
        {"emb": str(query_embedding), "top": top},
    )
    return rows.all()
