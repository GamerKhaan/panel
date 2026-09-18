"""add distinct GamerKhaan AmneziaWG core type

Revision ID: pgawg0001
Revises: 48a6bcb8bba1
"""

import sqlalchemy as sa
from alembic import op

revision = "pgawg0001"
down_revision = "48a6bcb8bba1"
branch_labels = None
depends_on = None

_OLD_VALUES = ("xray", "wg", "mtproto", "singbox")
_NEW_VALUES = ("xray", "wg", "gamerkhaan_amneziawg", "mtproto", "singbox")


def _core_enum(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="coretype")


def upgrade() -> None:
    dialect = op.get_bind().dialect.name

    if dialect == "postgresql":
        # PostgreSQL native ENUMs are extended in-place. ADD VALUE must run
        # outside the surrounding migration transaction on supported versions.
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE coretype ADD VALUE IF NOT EXISTS 'gamerkhaan_amneziawg'")
        return

    if dialect in {"mysql", "mariadb"}:
        # MySQL/MariaDB store the allowed values in the column definition.
        # Expanding the enum preserves all existing rows and the default.
        op.alter_column(
            "core_configs",
            "type",
            existing_type=_core_enum(_OLD_VALUES),
            type_=_core_enum(_NEW_VALUES),
            existing_nullable=False,
            existing_server_default="xray",
        )
        return

    if dialect == "sqlite":
        # SQLite represents SQLAlchemy Enum as VARCHAR(length). The original
        # four-value enum was VARCHAR(7); the AWG value requires a wider
        # representation. Batch mode rebuilds the table while preserving rows,
        # constraints and the server default.
        with op.batch_alter_table("core_configs") as batch:
            batch.alter_column(
                "type",
                existing_type=_core_enum(_OLD_VALUES),
                type_=_core_enum(_NEW_VALUES),
                existing_nullable=False,
                existing_server_default="xray",
            )


def downgrade() -> None:
    # Removing an enum value can destroy or invalidate stored AWG rows on every
    # supported backend. Keep the additive schema capability during rollback;
    # older application code simply does not emit the AWG value.
    pass
