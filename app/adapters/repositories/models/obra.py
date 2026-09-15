from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class ObraModel(Base):
    __tablename__ = "obra"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    isbn: Mapped[str] = mapped_column(String(20), nullable=False)
    titulo: Mapped[str] = mapped_column(String(512), nullable=False)
    autores: Mapped[list] = mapped_column(JSONB, nullable=False)
    editora: Mapped[str] = mapped_column(String(256), nullable=False)
    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    capa_url: Mapped[str] = mapped_column(String(1024), nullable=True)
    categoria: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
