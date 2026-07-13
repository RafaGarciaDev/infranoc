"""drop ivfflat index on knowledge_docs (unreliable with few rows)

Revision ID: a1b2c3d4e5f6
Revises: df80a00f2d2e
Create Date: 2026-07-12

O indice ivfflat com lists=100 retorna 0 resultados de forma
intermitente com poucas linhas na tabela (centroides treinados
vazios + probes=1). Busca exata (seq scan) e rapida e correta
nesta escala; recriar como HNSW quando a base crescer.
"""

from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "df80a00f2d2e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_docs_embedding")


def downgrade() -> None:
    op.execute(
        "CREATE INDEX ix_knowledge_docs_embedding ON knowledge_docs "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
