"""store complete node core version strings

Revision ID: pgawg0002
Revises: pgawg0001
"""

import sqlalchemy as sa
from alembic import op

revision = "pgawg0002"
down_revision = "pgawg0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("nodes") as batch_op:
        batch_op.alter_column(
            "xray_version",
            existing_type=sa.String(length=32),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    oversized = op.get_bind().execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM nodes WHERE char_length(xray_version) > 32)")
    ).scalar_one()
    if oversized:
        raise RuntimeError(
            "Refusing to narrow nodes.xray_version to 32 characters while longer values exist"
        )

    with op.batch_alter_table("nodes") as batch_op:
        batch_op.alter_column(
            "xray_version",
            existing_type=sa.Text(),
            type_=sa.String(length=32),
            existing_nullable=True,
        )
