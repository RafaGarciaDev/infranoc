"""add_new_asset_types_enum_values

Revision ID: 9355972f4313
Revises: 386119c921cd
Create Date: 2026-07-08

Adiciona valores novos ao enum Postgres `asset_type` para suportar
os equipamentos industriais da Fase 4.5.

Postgres nao permite ALTER TYPE ... ADD VALUE dentro de transacao,
por isso usamos IF NOT EXISTS + COMMIT explicito no upgrade.
O downgrade e no-op (Postgres nao suporta DROP VALUE em enums).
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '9355972f4313'
down_revision: Union[str, Sequence[str], None] = '386119c921cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_VALUES = [
    "Motor",
    "Tank",
    "AirCompressor",
    "SteamBoiler",
    "ChilledWaterPump",
    "BarcodeReader",
]


def upgrade() -> None:
    """Upgrade schema."""
    # ALTER TYPE ... ADD VALUE nao roda em transacao -> commit antes.
    op.execute("COMMIT")
    for v in NEW_VALUES:
        op.execute(f"ALTER TYPE asset_type ADD VALUE IF NOT EXISTS '{v}'")


def downgrade() -> None:
    """Downgrade schema. Postgres nao suporta remocao de valor de enum."""
    pass