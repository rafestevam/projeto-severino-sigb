from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base

AcaoInventarioLogEnum = Enum(
    "encontrado", "falta", "baixado", name="acaoinventariolog"
)


class InventarioLogModel(Base):
    __tablename__ = "inventario_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exemplar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exemplar.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    operador_keycloak_id: Mapped[str] = mapped_column(String(36), nullable=False)
    acao: Mapped[str] = mapped_column(AcaoInventarioLogEnum, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
