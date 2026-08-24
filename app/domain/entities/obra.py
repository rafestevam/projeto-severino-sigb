from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class Obra:
    id: UUID
    isbn: str
    titulo: str
    autores: list[str]
    editora: str
    ano: int
    capa_url: str
    categoria: str
    created_at: datetime
