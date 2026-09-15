from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.leitor import Leitor


class LeitorRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Leitor | None: ...

    @abstractmethod
    async def get_by_cpf_hash(self, cpf_hash: str) -> Leitor | None: ...

    @abstractmethod
    async def list_ativos(self) -> list[Leitor]: ...

    @abstractmethod
    async def save(self, leitor: Leitor) -> Leitor: ...
