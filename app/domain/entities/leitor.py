from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class Leitor:
    id: UUID
    nome: str
    cpf_hash: str
    telefone: str
    email: str
    ativo: bool
    created_at: datetime

    @classmethod
    def hash_cpf(cls, cpf: str) -> str:
        return hashlib.sha256(cpf.encode()).hexdigest()
