from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.inventario_log import InventarioLogModel
from app.domain.entities.inventario_log import InventarioLog
from app.domain.repositories.inventario_log_repository import InventarioLogRepository


def _to_entity(model: InventarioLogModel) -> InventarioLog:
    return InventarioLog(
        id=model.id,
        exemplar_id=model.exemplar_id,
        operador_keycloak_id=model.operador_keycloak_id,
        acao=model.acao,
        timestamp=model.timestamp,
    )


class SQLAlchemyInventarioLogRepository(InventarioLogRepository):
    """Concrete repository for persisting inventory audit log entries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def registrar(
        self,
        exemplar_id: UUID,
        operador_keycloak_id: str,
        acao: str,
    ) -> InventarioLog:
        """Insert a new inventory log entry and return the persisted entity."""
        entry = InventarioLogModel(
            id=uuid.uuid4(),
            exemplar_id=exemplar_id,
            operador_keycloak_id=operador_keycloak_id,
            acao=acao,
        )
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return _to_entity(entry)

    async def list_by_exemplar(self, exemplar_id: UUID) -> list[InventarioLog]:
        """Return all log entries for a given exemplar, newest first."""
        result = await self._session.execute(
            select(InventarioLogModel)
            .where(InventarioLogModel.exemplar_id == exemplar_id)
            .order_by(InventarioLogModel.timestamp.desc())
        )
        return [_to_entity(row) for row in result.scalars().all()]
