from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass(slots=True)
class Reserva:
    id: UUID
    obra_id: UUID
    leitor_id: UUID
    status: Literal["aguardando", "disponivel", "expirada", "atendida"]
    created_at: datetime
