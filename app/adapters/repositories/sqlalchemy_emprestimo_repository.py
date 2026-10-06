from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.emprestimo import EmprestimoModel
from app.adapters.repositories.models.exemplar import ExemplarModel
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

    async def get_ativo_by_exemplar_qr(self, codigo_qr: str) -> Emprestimo | None:
        result = await self._session.execute(
            select(EmprestimoModel)
            .join(ExemplarModel, EmprestimoModel.exemplar_id == ExemplarModel.id)
            .where(
                ExemplarModel.codigo_qr == codigo_qr,
                EmprestimoModel.status == "ativo",
            )
        )
        model = result.scalar_one_or_none()
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

    async def list_ativos_vencidos(self) -> list[Emprestimo]:
        result = await self._session.execute(
            select(EmprestimoModel).where(
                EmprestimoModel.status == "ativo",
                EmprestimoModel.data_prevista < func.now(),
            )
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def list_filtered(
        self,
        leitor_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Emprestimo], int]:
        base_query = select(EmprestimoModel)
        count_query = select(func.count()).select_from(EmprestimoModel)

        if leitor_id is not None:
            base_query = base_query.where(EmprestimoModel.leitor_id == leitor_id)
            count_query = count_query.where(EmprestimoModel.leitor_id == leitor_id)

        if status is not None:
            base_query = base_query.where(EmprestimoModel.status == status)
            count_query = count_query.where(EmprestimoModel.status == status)

        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        paginated_query = base_query.offset(offset).limit(page_size)
        result = await self._session.execute(paginated_query)
        items = [_to_entity(row) for row in result.scalars().all()]

        return items, total

    async def save(self, emprestimo: Emprestimo) -> Emprestimo:
        # Use explicit INSERT or UPDATE to avoid identity-map cache issues that
        # arise when multiple AsyncSession objects share the same connection
        # (as happens in the nested-transaction test fixture).
        existing = await self._session.get(EmprestimoModel, emprestimo.id)
        if existing is None:
            # New entity — INSERT
            model = _from_entity(emprestimo)
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model)
            return _to_entity(model)
        else:
            # Existing entity — UPDATE using raw SQL to guarantee the write
            # lands in the current SAVEPOINT and is visible to subsequent
            # sessions sharing the same connection (test isolation pattern).
            await self._session.execute(
                text(
                    "UPDATE emprestimo SET "
                    "data_prevista = :dp, "
                    "data_devolucao = :dd, "
                    "renovacoes = :r, "
                    "status = :s "
                    "WHERE id = :id"
                ),
                {
                    "dp": emprestimo.data_prevista,
                    "dd": emprestimo.data_devolucao,
                    "r": emprestimo.renovacoes,
                    "s": emprestimo.status,
                    "id": emprestimo.id,
                },
            )
            await self._session.flush()
            # expire + refresh ensures the returned entity reflects the
            # just-written values, not the stale identity-map state.
            self._session.expire(existing)
            await self._session.refresh(existing)
            return _to_entity(existing)

    async def count_ativos_by_leitor(self, leitor_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).where(
                EmprestimoModel.leitor_id == leitor_id,
                EmprestimoModel.status == "ativo",
            )
        )
        return result.scalar_one()

    async def list_com_vencimento_amanha(self) -> list[Emprestimo]:
        amanha = date.today() + timedelta(days=1)
        amanha_inicio = datetime(amanha.year, amanha.month, amanha.day, 0, 0, 0, tzinfo=timezone.utc)
        amanha_fim = datetime(amanha.year, amanha.month, amanha.day, 23, 59, 59, tzinfo=timezone.utc)
        result = await self._session.execute(
            select(EmprestimoModel).where(
                EmprestimoModel.status == "ativo",
                EmprestimoModel.data_prevista >= amanha_inicio,
                EmprestimoModel.data_prevista <= amanha_fim,
            )
        )
        return [_to_entity(row) for row in result.scalars().all()]
