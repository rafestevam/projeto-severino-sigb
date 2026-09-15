from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.obra import Obra


class ObraRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Obra | None: ...

    @abstractmethod
    async def get_by_isbn(self, isbn: str) -> Obra | None: ...

    @abstractmethod
    async def list_all(self) -> list[Obra]: ...

    @abstractmethod
    async def save(self, obra: Obra) -> Obra: ...

    @abstractmethod
    async def delete(self, id: UUID) -> None: ...
