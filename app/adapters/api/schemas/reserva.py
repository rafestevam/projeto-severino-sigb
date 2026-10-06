from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReservaIn(BaseModel):
    obra_id: UUID
    leitor_id: UUID


class ReservaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    obra_id: UUID
    leitor_id: UUID
    status: str
    created_at: datetime
    posicao_fila: int | None = None
