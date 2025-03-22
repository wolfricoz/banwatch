"""adding active to guild table

Revision ID: adb569f2001d
Revises: 486c5173808d
Create Date: 2025-03-22 00:01:48.844450

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'adb569f2001d'
down_revision: Union[str, None] = '486c5173808d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('servers', sa.Column('active', sa.Boolean(), nullable=True, default=False))


def downgrade() -> None:
    op.drop_column('servers', 'active')
