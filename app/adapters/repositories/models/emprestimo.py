from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base

StatusEmprestimoEnum = Enum(
    "ativo", "devolvido", "atrasado", name="statusemprestimo"
)


class EmprestimoModel(Base):
    __tablename__ = "emprestimo"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exemplar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exemplar.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    leitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leitor.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    data_checkout: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_prevista: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_devolucao: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    renovacoes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(StatusEmprestimoEnum, nullable=False)
