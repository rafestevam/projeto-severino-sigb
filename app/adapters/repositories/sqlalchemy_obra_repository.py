from __future__ import annotations

from uuid import UUID

from sqlalchemy import Text, func, select, text
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
        total_emprestimos=model.total_emprestimos,
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
        total_emprestimos=entity.total_emprestimos,
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

    async def list_filtered(
        self,
        titulo: str | None = None,
        autor: str | None = None,
        categoria: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Obra], int]:
        query = select(ObraModel)
        if titulo:
            query = query.where(ObraModel.titulo.ilike(f"%{titulo}%"))
        if autor:
            query = query.where(
                ObraModel.autores.cast(Text).ilike(f"%{autor}%")  # type: ignore[attr-defined]
            )
        if categoria:
            query = query.where(ObraModel.categoria.ilike(f"%{categoria}%"))

        count_result = await self._session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total: int = count_result.scalar_one()

        offset = (page - 1) * page_size
        rows_result = await self._session.execute(
            query.order_by(ObraModel.created_at.desc()).offset(offset).limit(page_size)
        )
        obras = [_to_entity(row) for row in rows_result.scalars().all()]
        return obras, total

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

    async def count_all(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(ObraModel))
        return result.scalar_one()

    async def list_top_emprestadas(self, limit: int = 10) -> list[Obra]:
        result = await self._session.execute(
            select(ObraModel)
            .order_by(ObraModel.total_emprestimos.desc())
            .limit(limit)
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def increment_total_emprestimos(self, obra_id: UUID) -> None:
        await self._session.execute(
            text("UPDATE obra SET total_emprestimos = total_emprestimos + 1 WHERE id = :id"),
            {"id": obra_id},
        )
        await self._session.flush()
