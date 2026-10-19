from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.value_objects.cpf import hash_cpf


@dataclass(slots=True)
class Leitor:
    id: UUID
    nome: str
    cpf_hash: str
    telefone: str | None
    email: str | None
    ativo: bool
    created_at: datetime

    @classmethod
    def hash_cpf(cls, cpf: str) -> str:
        return hash_cpf(cpf)
