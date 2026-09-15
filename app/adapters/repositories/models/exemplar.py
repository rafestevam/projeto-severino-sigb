from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base

EstadoExemplarEnum = Enum(
    "disponivel", "emprestado", "baixado", name="estadoexemplar"
)


class ExemplarModel(Base):
    __tablename__ = "exemplar"
    __table_args__ = (UniqueConstraint("codigo_qr", name="uq_exemplar_codigo_qr"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    obra_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("obra.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    codigo_qr: Mapped[str] = mapped_column(String(256), nullable=False)
    estado: Mapped[str] = mapped_column(EstadoExemplarEnum, nullable=False)
    localizacao_estante: Mapped[str] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
