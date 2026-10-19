"""0007_add_obra_sinopse_leitor_contato_opcional

Revision ID: a7b8c9d0e1f2
Revises: f123456789ab
Create Date: 2026-10-18 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f123456789ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """ST-08: sinopse da obra, e-mail opcional do leitor e índice por e-mail.

    `leitor.telefone` já é anulável desde a 0002.
    """
    op.add_column("obra", sa.Column("sinopse", sa.Text(), nullable=True))
    op.alter_column(
        "leitor", "email", existing_type=sa.String(length=256), nullable=True
    )
    op.create_index(
        "ix_leitor_email_lower", "leitor", [sa.text("lower(email)")], unique=False
    )


def downgrade() -> None:
    """Reverte 0007. Leitores sem e-mail recebem string vazia antes do NOT NULL."""
    op.drop_index("ix_leitor_email_lower", table_name="leitor")
    op.execute("UPDATE leitor SET email = '' WHERE email IS NULL")
    op.alter_column(
        "leitor", "email", existing_type=sa.String(length=256), nullable=False
    )
    op.drop_column("obra", "sinopse")
