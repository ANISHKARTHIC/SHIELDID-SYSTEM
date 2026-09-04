"""add app_releases table

Revision ID: c1d4a2f6e8b3
Revises: ab62ca54b6b7
Create Date: 2026-09-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d4a2f6e8b3'
down_revision: Union[str, Sequence[str], None] = '27ea6836421b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'app_releases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(), nullable=True),
        sa.Column('s3_key', sa.String(), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('release_notes', sa.String(), nullable=True),
        sa.Column('is_latest', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_app_releases_id'), 'app_releases', ['id'], unique=False)
    op.create_index(op.f('ix_app_releases_version'), 'app_releases', ['version'], unique=True)
    op.create_index(op.f('ix_app_releases_is_latest'), 'app_releases', ['is_latest'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_app_releases_is_latest'), table_name='app_releases')
    op.drop_index(op.f('ix_app_releases_version'), table_name='app_releases')
    op.drop_index(op.f('ix_app_releases_id'), table_name='app_releases')
    op.drop_table('app_releases')
