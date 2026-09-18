"""add distinct GamerKhaan AmneziaWG core type

Revision ID: pgawg0001
Revises: 48a6bcb8bba1
"""

from alembic import op

revision = "pgawg0001"
down_revision = "48a6bcb8bba1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE coretype ADD VALUE IF NOT EXISTS 'gamerkhaan_amneziawg'")


def downgrade() -> None:
    # PostgreSQL enum value removal requires a destructive type/table rewrite.
    # Retaining this additive value keeps rollback compatible with stored AWG rows.
    pass
