from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.leitor import LeitorModel
from app.domain.entities.leitor import Leitor
from app.domain.repositories.leitor_repository import LeitorRepository


def _to_entity(model: LeitorModel) -> Leitor:
    return Leitor(
        id=model.id,
        nome=model.nome,
        cpf_hash=model.cpf_hash,
        telefone=model.telefone,
        email=model.email,
        ativo=model.ativo,
        created_at=model.created_at,
    )


def _from_entity(entity: Leitor) -> LeitorModel:
    return LeitorModel(
        id=entity.id,
        nome=entity.nome,
        cpf_hash=entity.cpf_hash,
        telefone=entity.telefone,
        email=entity.email,
        ativo=entity.ativo,
        created_at=entity.created_at,
    )


class SQLAlchemyLeitorRepository(LeitorRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Leitor | None:
        model = await self._session.get(LeitorModel, id)
        return _to_entity(model) if model else None

    async def get_by_cpf_hash(self, cpf_hash: str) -> Leitor | None:
        result = await self._session.execute(
            select(LeitorModel).where(LeitorModel.cpf_hash == cpf_hash)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_ativos(self) -> list[Leitor]:
        result = await self._session.execute(
            select(LeitorModel).where(LeitorModel.ativo.is_(True))
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def save(self, leitor: Leitor) -> Leitor:
        model = _from_entity(leitor)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def ativar(self, id: UUID) -> Leitor | None:
        await self._session.execute(
            text("UPDATE leitor SET ativo = true WHERE id = :id"),
            {"id": id},
        )
        await self._session.flush()
        model = await self._session.get(LeitorModel, id)
        if model is None:
            return None
        self._session.expire(model)
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_email(self, email: str) -> Leitor | None:
        result = await self._session.execute(
            select(LeitorModel)
            .where(func.lower(LeitorModel.email) == email.strip().lower())
            .limit(2)
        )
        encontrados = result.scalars().all()
        if len(encontrados) != 1:
            return None
        return _to_entity(encontrados[0])
