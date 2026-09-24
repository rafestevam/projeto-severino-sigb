"""
Testes unitários para SQLAlchemyEmprestimoRepository com foco nos novos métodos.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.sqlalchemy_emprestimo_repository import (
    SQLAlchemyEmprestimoRepository,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session: AsyncMock) -> SQLAlchemyEmprestimoRepository:
    return SQLAlchemyEmprestimoRepository(mock_session)


class TestSQLAlchemyEmprestimoRepositoryNovosMetodos:
    @pytest.mark.asyncio
    async def test_get_ativo_by_exemplar_qr_encontrado(
        self, repo: SQLAlchemyEmprestimoRepository, mock_session: AsyncMock
    ) -> None:
        mock_model = MagicMock()
        mock_model.id = uuid4()
        mock_model.exemplar_id = uuid4()
        mock_model.leitor_id = uuid4()
        mock_model.data_checkout = MagicMock()
        mock_model.data_prevista = MagicMock()
        mock_model.data_devolucao = None
        mock_model.renovacoes = 0
        mock_model.status = "ativo"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        result = await repo.get_ativo_by_exemplar_qr("QR123")

        assert result is not None
        assert result.id == mock_model.id
        assert result.status == "ativo"
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_ativo_by_exemplar_qr_nao_encontrado(
        self, repo: SQLAlchemyEmprestimoRepository, mock_session: AsyncMock
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_ativo_by_exemplar_qr("QR_INEXISTENTE")

        assert result is None
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_filtered(
        self, repo: SQLAlchemyEmprestimoRepository, mock_session: AsyncMock
    ) -> None:
        mock_model = MagicMock()
        mock_model.id = uuid4()
        mock_model.exemplar_id = uuid4()
        mock_model.leitor_id = uuid4()
        mock_model.data_checkout = MagicMock()
        mock_model.data_prevista = MagicMock()
        mock_model.data_devolucao = None
        mock_model.renovacoes = 0
        mock_model.status = "ativo"

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        items_result = MagicMock()
        items_scalars = MagicMock()
        items_scalars.all.return_value = [mock_model]
        items_result.scalars.return_value = items_scalars

        mock_session.execute.side_effect = [count_result, items_result]

        items, total = await repo.list_filtered(leitor_id=mock_model.leitor_id, status="ativo")

        assert total == 1
        assert len(items) == 1
        assert items[0].id == mock_model.id
        assert mock_session.execute.await_count == 2
