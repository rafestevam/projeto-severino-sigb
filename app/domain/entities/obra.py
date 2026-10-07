from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class Obra:
    id: UUID
    isbn: str | None
    titulo: str
    autores: list[str]
    editora: str
    ano: int
    capa_url: str
    categoria: str
    created_at: datetime
    total_emprestimos: int = field(default=0)
