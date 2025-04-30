"""Add processing time field

Revision ID: c05bc1155194
Revises: b05bc1155193
Create Date: 2025-04-30 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c05bc1155194'
down_revision: Union[str, None] = 'b05bc1155193'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('validation_requests', sa.Column('processing_time', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('validation_requests', 'processing_time')
