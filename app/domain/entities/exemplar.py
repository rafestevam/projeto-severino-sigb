from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass(slots=True)
class Exemplar:
    id: UUID
    obra_id: UUID
    codigo_qr: str
    estado: Literal["disponivel", "emprestado", "baixado"]
    localizacao_estante: str
    created_at: datetime
    origem: str | None = field(default=None)
    motivo_baixa: str | None = field(default=None)
