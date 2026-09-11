from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.emprestimo import EmprestimoModel
from app.domain.entities.emprestimo import Emprestimo
from app.domain.repositories.emprestimo_repository import EmprestimoRepository


def _to_entity(model: EmprestimoModel) -> Emprestimo:
    return Emprestimo(
        id=model.id,
        exemplar_id=model.exemplar_id,
        leitor_id=model.leitor_id,
        data_checkout=model.data_checkout,
        data_prevista=model.data_prevista,
        data_devolucao=model.data_devolucao,
        renovacoes=model.renovacoes,
        status=model.status,
    )


def _from_entity(entity: Emprestimo) -> EmprestimoModel:
    return EmprestimoModel(
        id=entity.id,
        exemplar_id=entity.exemplar_id,
        leitor_id=entity.leitor_id,
        data_checkout=entity.data_checkout,
        data_prevista=entity.data_prevista,
        data_devolucao=entity.data_devolucao,
        renovacoes=entity.renovacoes,
        status=entity.status,
    )


class SQLAlchemyEmprestimoRepository(EmprestimoRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Emprestimo | None:
        model = await self._session.get(EmprestimoModel, id)
        return _to_entity(model) if model else None

    async def list_by_leitor(self, leitor_id: UUID) -> list[Emprestimo]:
        result = await self._session.execute(
            select(EmprestimoModel).where(EmprestimoModel.leitor_id == leitor_id)
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def list_ativos(self) -> list[Emprestimo]:
        result = await self._session.execute(
            select(EmprestimoModel).where(EmprestimoModel.status == "ativo")
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def save(self, emprestimo: Emprestimo) -> Emprestimo:
        model = _from_entity(emprestimo)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def count_ativos_by_leitor(self, leitor_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).where(
                EmprestimoModel.leitor_id == leitor_id,
                EmprestimoModel.status == "ativo",
            )
        )
        return result.scalar_one()
