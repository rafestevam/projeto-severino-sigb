from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.exemplar import ExemplarModel
from app.domain.entities.exemplar import Exemplar
from app.domain.repositories.exemplar_repository import ExemplarRepository


def _to_entity(model: ExemplarModel) -> Exemplar:
    return Exemplar(
        id=model.id,
        obra_id=model.obra_id,
        codigo_qr=model.codigo_qr,
        estado=model.estado,
        localizacao_estante=model.localizacao_estante,
        created_at=model.created_at,
    )


def _from_entity(entity: Exemplar) -> ExemplarModel:
    return ExemplarModel(
        id=entity.id,
        obra_id=entity.obra_id,
        codigo_qr=entity.codigo_qr,
        estado=entity.estado,
        localizacao_estante=entity.localizacao_estante,
        created_at=entity.created_at,
    )


class SQLAlchemyExemplarRepository(ExemplarRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Exemplar | None:
        model = await self._session.get(ExemplarModel, id)
        return _to_entity(model) if model else None

    async def get_by_codigo_qr(self, codigo_qr: str) -> Exemplar | None:
        result = await self._session.execute(
            select(ExemplarModel).where(ExemplarModel.codigo_qr == codigo_qr)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_by_obra(self, obra_id: UUID) -> list[Exemplar]:
        result = await self._session.execute(
            select(ExemplarModel).where(ExemplarModel.obra_id == obra_id)
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def save(self, exemplar: Exemplar) -> Exemplar:
        model = _from_entity(exemplar)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update_estado(self, id: UUID, estado: str) -> Exemplar | None:
        model = await self._session.get(ExemplarModel, id)
        if model is None:
            return None
        model.estado = estado
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)
