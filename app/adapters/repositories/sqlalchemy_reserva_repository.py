from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.reserva import ReservaModel
from app.domain.entities.reserva import Reserva
from app.domain.repositories.reserva_repository import ReservaRepository


def _to_entity(model: ReservaModel) -> Reserva:
    return Reserva(
        id=model.id,
        obra_id=model.obra_id,
        leitor_id=model.leitor_id,
        status=model.status,
        created_at=model.created_at,
    )


def _from_entity(entity: Reserva) -> ReservaModel:
    return ReservaModel(
        id=entity.id,
        obra_id=entity.obra_id,
        leitor_id=entity.leitor_id,
        status=entity.status,
        created_at=entity.created_at,
    )


class SQLAlchemyReservaRepository(ReservaRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Reserva | None:
        model = await self._session.get(ReservaModel, id)
        return _to_entity(model) if model else None

    async def list_by_obra(self, obra_id: UUID) -> list[Reserva]:
        result = await self._session.execute(
            select(ReservaModel).where(ReservaModel.obra_id == obra_id)
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def get_proxima_aguardando(self, obra_id: UUID) -> Reserva | None:
        result = await self._session.execute(
            select(ReservaModel)
            .where(
                ReservaModel.obra_id == obra_id,
                ReservaModel.status == "aguardando",
            )
            .order_by(ReservaModel.created_at.asc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def save(self, reserva: Reserva) -> Reserva:
        model = _from_entity(reserva)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update_status(self, id: UUID, status: str) -> Reserva | None:
        model = await self._session.get(ReservaModel, id)
        if model is None:
            return None
        model.status = status
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)
