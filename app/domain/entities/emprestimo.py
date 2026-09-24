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


@dataclass(slots=True)
class EmprestimoComTitulo:
    """DTO that combines a loan with its associated obra title.

    The ``titulo_obra`` field is resolved by the use case layer via
    ExemplarRepository + ObraRepository.  This DTO is intentionally
    read-only at the domain level — it carries no mutation behaviour.
    """

    id: UUID
    exemplar_id: UUID
    leitor_id: UUID
    data_checkout: datetime
    data_prevista: datetime
    data_devolucao: datetime | None
    renovacoes: int
    status: Literal["ativo", "devolvido", "atrasado"]
    titulo_obra: str
