"""0004_add_configuracao

Revision ID: d123456789ab
Revises: c123456789ab
Create Date: 2026-08-25 10:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d123456789ab"
down_revision: Union[str, Sequence[str], None] = "c123456789ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    configuracao_table = op.create_table(
        "configuracao",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chave", sa.String(length=100), nullable=False),
        sa.Column("valor", sa.String(length=255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chave"),
    )
    op.create_index(op.f("ix_configuracao_chave"), "configuracao", ["chave"], unique=True)

    # Seed default values
    op.bulk_insert(
        configuracao_table,
        [
            {
                "id": uuid.uuid4(),
                "chave": "dias_emprestimo",
                "valor": "14",
            },
            {
                "id": uuid.uuid4(),
                "chave": "max_renovacoes",
                "valor": "3",
            },
            {
                "id": uuid.uuid4(),
                "chave": "max_emprestimos_por_leitor",
                "valor": "3",
            },
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_configuracao_chave"), table_name="configuracao")
    op.drop_table("configuracao")
