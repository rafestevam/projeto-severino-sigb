from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass(slots=True)
class Emprestimo:
    id: UUID
    exemplar_id: UUID
    leitor_id: UUID
    data_checkout: datetime
    data_prevista: datetime
    data_devolucao: datetime | None
    renovacoes: int
    status: Literal["ativo", "devolvido", "atrasado"]
