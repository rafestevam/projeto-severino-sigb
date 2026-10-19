"""
Testes unitários para os métodos do OPAC (ST-08) nos repositórios SQLAlchemy.

Estratégia: AsyncSession mockada; as consultas emitidas são compiladas para o
dialeto PostgreSQL e inspecionadas. O comportamento contra um banco real é
coberto em tests/e2e/st_08_opac/.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.sqlalchemy_exemplar_repository import (
    SQLAlchemyExemplarRepository,
)
from app.adapters.repositories.sqlalchemy_leitor_repository import (
    SQLAlchemyLeitorRepository,
)
from app.adapters.repositories.sqlalchemy_obra_repository import (
    SQLAlchemyObraRepository,
    _padrao_contem,
)
from app.domain.entities.disponibilidade_obra import DisponibilidadeObra


def _sql(statement) -> str:
    return str(statement.compile(dialect=postgresql.dialect())).lower()


def _result(*, scalar_one=None, scalar_one_or_none=None, scalars=None, rows=None) -> MagicMock:
    result = MagicMock()
    result.scalar_one.return_value = scalar_one
    result.scalar_one_or_none.return_value = scalar_one_or_none
    result.scalars.return_value.all.return_value = scalars or []
    result.all.return_value = rows or []
    return result


@pytest.fixture
def session() -> AsyncMock:
    s = AsyncMock(spec=AsyncSession)
    s.execute = AsyncMock()
    s.expire = MagicMock()
    return s


class TestPadraoContem:
    def test_envolve_termo_com_curingas(self) -> None:
        assert _padrao_contem("dom") == "%dom%"

    def test_escapa_curingas_do_termo(self) -> None:
        assert _padrao_contem("50%_off") == "%50\\%\\_off%"

    def test_escapa_a_propria_barra(self) -> None:
        assert _padrao_contem("a\\b") == "%a\\\\b%"


class TestBuscarCatalogoPublico:
    async def test_combina_campos_com_or_e_exige_exemplar_ativo(self, session: AsyncMock) -> None:
        session.execute.side_effect = [_result(scalar_one=0), _result(scalars=[])]

        await SQLAlchemyObraRepository(session).buscar_catalogo_publico("machado", 1, 20)

        sql = _sql(session.execute.await_args_list[1].args[0])
        assert "exists" in sql
        assert "exemplar.estado !=" in sql
        assert " or " in sql
        assert sql.count("ilike") == 3
        assert "escape" in sql
        assert "order by obra.titulo" in sql

    async def test_sem_termo_nao_filtra_por_texto(self, session: AsyncMock) -> None:
        session.execute.side_effect = [_result(scalar_one=0), _result(scalars=[])]

        await SQLAlchemyObraRepository(session).buscar_catalogo_publico("   ", 1, 20)

        sql = _sql(session.execute.await_args_list[1].args[0])
        assert "ilike" not in sql
        assert "exists" in sql

    async def test_aplica_offset_da_pagina(self, session: AsyncMock) -> None:
        session.execute.side_effect = [_result(scalar_one=45), _result(scalars=[])]

        _, total = await SQLAlchemyObraRepository(session).buscar_catalogo_publico(None, 3, 20)

        stmt = session.execute.await_args_list[1].args[0]
        params = stmt.compile(dialect=postgresql.dialect()).params
        assert total == 45
        assert {20, 40} <= set(params.values())  # limit=page_size, offset=(3-1)*20


class TestGetPosicaoRanking:
    async def test_none_quando_obra_inexistente(self, session: AsyncMock) -> None:
        session.execute.return_value = _result(scalar_one_or_none=None)
        assert await SQLAlchemyObraRepository(session).get_posicao_ranking(uuid4()) is None

    async def test_none_quando_nunca_emprestada(self, session: AsyncMock) -> None:
        session.execute.return_value = _result(scalar_one_or_none=0)
        assert await SQLAlchemyObraRepository(session).get_posicao_ranking(uuid4()) is None
        session.execute.assert_awaited_once()

    async def test_posicao_e_um_mais_obras_com_mais_emprestimos(self, session: AsyncMock) -> None:
        session.execute.side_effect = [_result(scalar_one_or_none=7), _result(scalar_one=2)]

        posicao = await SQLAlchemyObraRepository(session).get_posicao_ranking(uuid4())

        assert posicao == 3
        assert "total_emprestimos >" in _sql(session.execute.await_args_list[1].args[0])


class TestContarDisponibilidade:
    async def test_lista_vazia_nao_consulta_banco(self, session: AsyncMock) -> None:
        assert await SQLAlchemyExemplarRepository(session).contar_disponibilidade([]) == {}
        session.execute.assert_not_awaited()

    async def test_agrega_por_obra_em_uma_consulta(self, session: AsyncMock) -> None:
        a, b = uuid4(), uuid4()
        session.execute.return_value = _result(
            rows=[(a, "disponivel", 2), (a, "emprestado", 1), (b, "emprestado", 3)]
        )

        resultado = await SQLAlchemyExemplarRepository(session).contar_disponibilidade([a, b])

        assert resultado == {
            a: DisponibilidadeObra(a, disponiveis=2, emprestados=1),
            b: DisponibilidadeObra(b, disponiveis=0, emprestados=3),
        }
        session.execute.assert_awaited_once()
        sql = _sql(session.execute.await_args.args[0])
        assert "group by exemplar.obra_id, exemplar.estado" in sql
        assert "exemplar.estado !=" in sql


class TestLeitorAtivar:
    async def test_executa_update_explicito_e_recarrega(self, session: AsyncMock) -> None:
        model = MagicMock(
            id=uuid4(), nome="Ana", cpf_hash="h", telefone=None, email=None, ativo=True,
            created_at=MagicMock(),
        )
        session.get = AsyncMock(return_value=model)

        leitor = await SQLAlchemyLeitorRepository(session).ativar(model.id)

        assert leitor is not None and leitor.ativo is True
        assert "update leitor set ativo = true" in str(session.execute.await_args.args[0]).lower()
        session.flush.assert_awaited_once()
        session.expire.assert_called_once_with(model)
        session.refresh.assert_awaited_once_with(model)

    async def test_retorna_none_para_id_inexistente(self, session: AsyncMock) -> None:
        session.get = AsyncMock(return_value=None)
        assert await SQLAlchemyLeitorRepository(session).ativar(uuid4()) is None


class TestLeitorGetByEmail:
    def _model(self) -> MagicMock:
        return MagicMock(
            id=uuid4(), nome="Ana", cpf_hash="h", telefone=None, email="ana@ex.com",
            ativo=True, created_at=MagicMock(),
        )

    async def test_compara_em_minusculas(self, session: AsyncMock) -> None:
        session.execute.return_value = _result(scalars=[self._model()])

        leitor = await SQLAlchemyLeitorRepository(session).get_by_email(" Ana@Ex.COM ")

        assert leitor is not None
        stmt = session.execute.await_args.args[0]
        assert "lower(leitor.email)" in _sql(stmt)
        assert "ana@ex.com" in stmt.compile(dialect=postgresql.dialect()).params.values()

    async def test_none_quando_nao_encontrado(self, session: AsyncMock) -> None:
        session.execute.return_value = _result(scalars=[])
        assert await SQLAlchemyLeitorRepository(session).get_by_email("x@ex.com") is None

    async def test_none_quando_vinculo_ambiguo(self, session: AsyncMock) -> None:
        session.execute.return_value = _result(scalars=[self._model(), self._model()])
        assert await SQLAlchemyLeitorRepository(session).get_by_email("ana@ex.com") is None
