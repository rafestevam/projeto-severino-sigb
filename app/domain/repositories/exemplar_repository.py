from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.exemplar import Exemplar


class ExemplarRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Exemplar | None: ...

    @abstractmethod
    async def get_by_codigo_qr(self, codigo_qr: str) -> Exemplar | None: ...

    @abstractmethod
    async def list_by_obra(self, obra_id: UUID) -> list[Exemplar]: ...

    @abstractmethod
    async def save(self, exemplar: Exemplar) -> Exemplar: ...

    @abstractmethod
    async def update_estado(self, id: UUID, estado: str) -> Exemplar | None: ...

    @abstractmethod
    async def count_all(self) -> int: ...

    @abstractmethod
    async def list_by_localizacao(self, localizacao: str) -> list[Exemplar]: ...

    @abstractmethod
    async def update_baixa(self, id: UUID, motivo_baixa: str) -> Exemplar | None: ...

    @abstractmethod
    async def count_by_estado(self) -> dict[str, int]: ...

    @abstractmethod
    async def count_baixados_por_motivo(self, motivo: str) -> int: ...

    @abstractmethod
    async def count_by_origem(self, origem: str) -> int: ...
