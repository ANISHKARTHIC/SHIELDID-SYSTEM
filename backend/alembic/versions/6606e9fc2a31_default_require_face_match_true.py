"""Default require_face_match to True

A venue whose policy row was auto-created (venue_service.get_venue_policy)
inherited the Column-level Python default of False, meaning face-match
enforcement was silently off unless an admin explicitly opted in. This
defeats the purpose of the face-verification step in the decision logic
(v1_router.face_match): a low or missing face_similarity would never block
a PASS. Flip the server-side default to True and backfill any existing
rows that are False/NULL so already-provisioned venues also get the
correct behavior going forward, without touching venues that have
explicitly opted out via an actual policy update (which would show up as
False here regardless — this migration cannot distinguish "never touched"
from "explicitly disabled", so this is a one-time flip aligned with fixing
the fail-open default; any venue that wants it off can re-disable it
after this migration).

Revision ID: 6606e9fc2a31
Revises: a64f7462df04
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6606e9fc2a31'
down_revision: Union[str, Sequence[str], None] = 'a64f7462df04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'policy_schemas',
        'require_face_match',
        server_default=sa.true(),
    )
    op.execute(
        "UPDATE policy_schemas SET require_face_match = TRUE "
        "WHERE require_face_match IS NOT TRUE"
    )


def downgrade() -> None:
    op.alter_column(
        'policy_schemas',
        'require_face_match',
        server_default=sa.false(),
    )
