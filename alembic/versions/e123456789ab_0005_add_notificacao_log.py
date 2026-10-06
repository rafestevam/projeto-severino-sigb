"""0005_add_notificacao_log

Revision ID: e123456789ab
Revises: d123456789ab
Create Date: 2026-08-25 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e123456789ab"
down_revision: Union[str, Sequence[str], None] = "d123456789ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add notificacao_log table for audit trail of notification attempts."""
    op.create_table(
        "notificacao_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("leitor_id", sa.UUID(), nullable=False),
        sa.Column("template", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["leitor_id"], ["leitor.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notificacao_log_leitor_id"),
        "notificacao_log",
        ["leitor_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop notificacao_log — must run before leitor table can be dropped."""
    op.drop_index(op.f("ix_notificacao_log_leitor_id"), table_name="notificacao_log")
    op.drop_table("notificacao_log")
