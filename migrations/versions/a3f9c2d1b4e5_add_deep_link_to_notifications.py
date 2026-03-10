"""add_deep_link_to_notifications

Revision ID: a3f9c2d1b4e5
Revises: 147458278fe6
Create Date: 2026-03-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f9c2d1b4e5'
down_revision: Union[str, Sequence[str], None] = '147458278fe6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('notifications', sa.Column('deep_link_type', sa.String(), nullable=True, server_default='none'))
    op.add_column('notifications', sa.Column('deep_link_id', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('notifications', 'deep_link_id')
    op.drop_column('notifications', 'deep_link_type')
