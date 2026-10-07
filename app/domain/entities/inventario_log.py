from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass(slots=True)
class InventarioLog:
    id: UUID
    exemplar_id: UUID
    operador_keycloak_id: str
    acao: Literal["encontrado", "falta", "baixado"]
    timestamp: datetime
