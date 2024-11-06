"""add hidden toggle to servers

Revision ID: 486c5173808d
Revises: 
Create Date: 2024-11-06 16:06:18.451859

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '486c5173808d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('servers', sa.Column('hidden', sa.Boolean, default=False, nullable=False))


def downgrade() -> None:
    op.drop_column('servers', 'hidden')
