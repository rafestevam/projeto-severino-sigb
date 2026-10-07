"""0006_add_exemplar_origem_motivo_baixa_obra_total_emprestimos

Revision ID: f123456789ab
Revises: e123456789ab
Create Date: 2026-08-26 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f123456789ab"
down_revision: Union[str, Sequence[str], None] = "e123456789ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add origem and motivo_baixa to exemplar; add total_emprestimos to obra."""
    op.add_column(
        "exemplar",
        sa.Column("origem", sa.String(20), nullable=True),
    )
    op.add_column(
        "exemplar",
        sa.Column("motivo_baixa", sa.Text(), nullable=True),
    )
    op.add_column(
        "obra",
        sa.Column(
            "total_emprestimos",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    pass
