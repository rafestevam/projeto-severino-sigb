from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExemplarBatchIn(BaseModel):
    quantidade: int = Field(ge=1)
    localizacao_estante: str


class ExemplarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    obra_id: UUID
    codigo_qr: str
    estado: str
    localizacao_estante: str
    created_at: datetime
