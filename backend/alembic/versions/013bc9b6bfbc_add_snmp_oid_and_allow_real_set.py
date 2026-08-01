"""add snmp oid/value_type to device_commands and allow_real_snmp_set to device_protocol_profiles

Revision ID: 013bc9b6bfbc
Revises: cb508ac7501d
Create Date: 2026-08-01 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '013bc9b6bfbc'
down_revision: Union[str, Sequence[str], None] = 'cb508ac7501d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('device_commands', sa.Column('oid', sa.String(length=128), nullable=True))
    op.add_column('device_commands', sa.Column('value_type', sa.String(length=16), nullable=True))
    op.add_column(
        'device_protocol_profiles',
        sa.Column('allow_real_snmp_set', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('device_protocol_profiles', 'allow_real_snmp_set')
    op.drop_column('device_commands', 'value_type')
    op.drop_column('device_commands', 'oid')
