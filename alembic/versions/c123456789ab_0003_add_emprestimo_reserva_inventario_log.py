"""0003_add_emprestimo_reserva_inventario_log

Revision ID: c123456789ab
Revises: b9cb64000fbf
Create Date: 2026-08-24 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c123456789ab"
down_revision: Union[str, Sequence[str], None] = "b9cb64000fbf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Use postgresql.ENUM for Postgres-specific ENUMs without autogeneration side-effects
    from sqlalchemy.dialects.postgresql import ENUM as pg_ENUM
    emprestimo_status_enum = pg_ENUM(
        "ativo",
        "devolvido",
        "atrasado",
        name="statusemprestimo",
        create_type=False,
    )
    reserva_status_enum = pg_ENUM(
        "aguardando",
        "disponivel",
        "expirada",
        "atendida",
        name="statusreserva",
        create_type=False,
    )
    inventario_acao_enum = pg_ENUM(
        "encontrado",
        "falta",
        "baixado",
        name="acaoinventariolog",
        create_type=False,
    )

    # Manual type creation using op.execute if types do not exist
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'statusemprestimo') THEN "
        "CREATE TYPE statusemprestimo AS ENUM ('ativo', 'devolvido', 'atrasado'); "
        "END IF; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'statusreserva') THEN "
        "CREATE TYPE statusreserva AS ENUM ('aguardando', 'disponivel', 'expirada', 'atendida'); "
        "END IF; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'acaoinventariolog') THEN "
        "CREATE TYPE acaoinventariolog AS ENUM ('encontrado', 'falta', 'baixado'); "
        "END IF; END $$;"
    )

    op.create_table(
        "emprestimo",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("exemplar_id", sa.UUID(), nullable=False),
        sa.Column("leitor_id", sa.UUID(), nullable=False),
        sa.Column("data_checkout", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_prevista", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_devolucao", sa.DateTime(timezone=True), nullable=True),
        sa.Column("renovacoes", sa.Integer(), nullable=False),
        sa.Column("status", emprestimo_status_enum, nullable=False),
        sa.ForeignKeyConstraint(["exemplar_id"], ["exemplar.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["leitor_id"], ["leitor.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_emprestimo_exemplar_id"), "emprestimo", ["exemplar_id"], unique=False)
    op.create_index(op.f("ix_emprestimo_leitor_id"), "emprestimo", ["leitor_id"], unique=False)

    op.create_table(
        "reserva",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("obra_id", sa.UUID(), nullable=False),
        sa.Column("leitor_id", sa.UUID(), nullable=False),
        sa.Column("status", reserva_status_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["obra_id"], ["obra.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["leitor_id"], ["leitor.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reserva_leitor_id"), "reserva", ["leitor_id"], unique=False)
    op.create_index(op.f("ix_reserva_obra_id"), "reserva", ["obra_id"], unique=False)

    op.create_table(
        "inventario_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("exemplar_id", sa.UUID(), nullable=False),
        sa.Column("operador_keycloak_id", sa.String(length=36), nullable=False),
        sa.Column("acao", inventario_acao_enum, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["exemplar_id"], ["exemplar.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventario_log_exemplar_id"), "inventario_log", ["exemplar_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_inventario_log_exemplar_id"), table_name="inventario_log")
    op.drop_table("inventario_log")
    op.drop_index(op.f("ix_reserva_obra_id"), table_name="reserva")
    op.drop_index(op.f("ix_reserva_leitor_id"), table_name="reserva")
    op.drop_table("reserva")
    op.drop_index(op.f("ix_emprestimo_leitor_id"), table_name="emprestimo")
    op.drop_index(op.f("ix_emprestimo_exemplar_id"), table_name="emprestimo")
    op.drop_table("emprestimo")
    op.execute("DROP TYPE IF EXISTS acaoinventariolog;")
    op.execute("DROP TYPE IF EXISTS statusreserva;")
    op.execute("DROP TYPE IF EXISTS statusemprestimo;")
