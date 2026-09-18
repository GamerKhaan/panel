"""bind observed AWG provenance to the node control identity

Revision ID: pgawg0003
Revises: pgawg0002
"""

import sqlalchemy as sa
from alembic import op

revision = "pgawg0003"
down_revision = "pgawg0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "nodes",
        sa.Column("awg_provenance_fingerprint", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("nodes", "awg_provenance_fingerprint")
