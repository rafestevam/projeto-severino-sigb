from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.reserva import Reserva


class ReservaRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Reserva | None: ...

    @abstractmethod
    async def list_by_obra(self, obra_id: UUID) -> list[Reserva]: ...

    @abstractmethod
    async def get_proxima_aguardando(self, obra_id: UUID) -> Reserva | None: ...

    @abstractmethod
    async def save(self, reserva: Reserva) -> Reserva: ...

    @abstractmethod
    async def update_status(self, id: UUID, status: str) -> Reserva | None: ...
