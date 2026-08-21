"""Unique open occupancy per venue+customer

Prevents concurrent duplicate check-ins: without a DB-level constraint, two
concurrent finalize_session calls for the same customer at the same venue
(duplicate submit, or two operator devices scanning the same person) could
each insert their own open (exited_at IS NULL) occupancy_records row,
inflating the live occupancy count. A single checkout only closes one row
(occupancy_service.check_out_by_customer uses .first()), permanently
leaking a phantom occupant into the count.

Before adding the constraint, close all but the most-recently-entered open
row for any (venue_id, customer_id) pair that already has duplicates, so
the migration doesn't fail against existing data. Closed-out duplicates are
marked AUTO_EXPIRED with exited_at = entered_at of the row that superseded
them, since we have no real checkout time to attribute.

Revision ID: 27ea6836421b
Revises: 6606e9fc2a31
Create Date: 2026-08-21 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27ea6836421b'
down_revision: Union[str, Sequence[str], None] = '6606e9fc2a31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT id, venue_id, customer_id, entered_at,
                   ROW_NUMBER() OVER (
                       PARTITION BY venue_id, customer_id
                       ORDER BY entered_at DESC, id DESC
                   ) AS rn
            FROM occupancy_records
            WHERE exited_at IS NULL
        )
        UPDATE occupancy_records o
        SET exited_at = keep.entered_at,
            status = 'AUTO_EXPIRED'
        FROM ranked dup
        JOIN ranked keep
          ON keep.venue_id = dup.venue_id
         AND keep.customer_id = dup.customer_id
         AND keep.rn = 1
        WHERE o.id = dup.id
          AND dup.rn > 1
        """
    )
    op.create_index(
        'uq_occupancy_open_per_venue_customer',
        'occupancy_records',
        ['venue_id', 'customer_id'],
        unique=True,
        postgresql_where=sa.text('exited_at IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_occupancy_open_per_venue_customer', table_name='occupancy_records')
