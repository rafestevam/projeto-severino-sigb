from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.obra import ObraModel
from app.domain.entities.obra import Obra
from app.domain.repositories.obra_repository import ObraRepository


def _to_entity(model: ObraModel) -> Obra:
    return Obra(
        id=model.id,
        isbn=model.isbn,
        titulo=model.titulo,
        autores=list(model.autores),
        editora=model.editora,
        ano=model.ano,
        capa_url=model.capa_url,
        categoria=model.categoria,
        created_at=model.created_at,
    )


def _from_entity(entity: Obra) -> ObraModel:
    return ObraModel(
        id=entity.id,
        isbn=entity.isbn,
        titulo=entity.titulo,
        autores=entity.autores,
        editora=entity.editora,
        ano=entity.ano,
        capa_url=entity.capa_url,
        categoria=entity.categoria,
        created_at=entity.created_at,
    )


class SQLAlchemyObraRepository(ObraRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Obra | None:
        model = await self._session.get(ObraModel, id)
        return _to_entity(model) if model else None

    async def get_by_isbn(self, isbn: str) -> Obra | None:
        result = await self._session.execute(
            select(ObraModel).where(ObraModel.isbn == isbn)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_all(self) -> list[Obra]:
        result = await self._session.execute(select(ObraModel))
        return [_to_entity(row) for row in result.scalars().all()]

    async def save(self, obra: Obra) -> Obra:
        model = _from_entity(obra)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def delete(self, id: UUID) -> None:
        model = await self._session.get(ObraModel, id)
        if model:
            await self._session.delete(model)
            await self._session.flush()
