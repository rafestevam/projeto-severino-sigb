from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CheckoutIn(BaseModel):
    exemplar_id: UUID
    leitor_id: UUID


class DevolucaoQrIn(BaseModel):
    codigo_qr: str


class EmprestimoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exemplar_id: UUID
    leitor_id: UUID
    titulo_obra: str | None = None
    data_checkout: datetime
    data_prevista: datetime
    data_devolucao: datetime | None = None
    status: str
    renovacoes: int


class EmprestimoListOut(BaseModel):
    items: list[EmprestimoOut]
    total: int
    page: int
    page_size: int
