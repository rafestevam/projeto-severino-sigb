from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.inventario_log import InventarioLog


class InventarioLogRepository(ABC):
    @abstractmethod
    async def registrar(
        self,
        exemplar_id: UUID,
        operador_keycloak_id: str,
        acao: str,
    ) -> InventarioLog: ...

    @abstractmethod
    async def list_by_exemplar(self, exemplar_id: UUID) -> list[InventarioLog]: ...
