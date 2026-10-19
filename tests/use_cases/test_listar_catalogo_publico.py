"""
Testes unitários para ListarCatalogoPublicoUseCase (US-028).

Estratégia: AsyncMock para os repositórios — sem banco de dados.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.domain.entities.disponibilidade_obra import DisponibilidadeObra
from app.use_cases.listar_catalogo_publico import ListarCatalogoPublicoUseCase
from tests.domain.repositories.conftest import make_obra


def _build(obras, total, disponibilidades):
    obra_repo = MagicMock()
    obra_repo.buscar_catalogo_publico = AsyncMock(return_value=(obras, total))
    exemplar_repo = MagicMock()
    exemplar_repo.contar_disponibilidade = AsyncMock(return_value=disponibilidades)
    return obra_repo, exemplar_repo


async def test_delega_busca_com_termo_e_paginacao() -> None:
    obra_repo, exemplar_repo = _build([], 0, {})

    await ListarCatalogoPublicoUseCase(obra_repo, exemplar_repo).execute("machado", 2, 10)

    obra_repo.buscar_catalogo_publico.assert_awaited_once_with("machado", 2, 10)


async def test_consulta_disponibilidade_uma_unica_vez_para_a_pagina() -> None:
    a, b = make_obra(id=uuid4()), make_obra(id=uuid4())
    obra_repo, exemplar_repo = _build([a, b], 2, {})

    await ListarCatalogoPublicoUseCase(obra_repo, exemplar_repo).execute(None, 1, 20)

    exemplar_repo.contar_disponibilidade.assert_awaited_once_with([a.id, b.id])


async def test_combina_obra_e_disponibilidade_preservando_ordem() -> None:
    a, b = make_obra(id=uuid4(), titulo="A"), make_obra(id=uuid4(), titulo="B")
    disp_a = DisponibilidadeObra(a.id, disponiveis=1, emprestados=0)
    disp_b = DisponibilidadeObra(b.id, disponiveis=0, emprestados=2)
    obra_repo, exemplar_repo = _build([a, b], 7, {a.id: disp_a, b.id: disp_b})

    pagina = await ListarCatalogoPublicoUseCase(obra_repo, exemplar_repo).execute(None, 1, 2)

    assert [i.obra.titulo for i in pagina.itens] == ["A", "B"]
    assert pagina.itens[0].disponibilidade.disponivel is True
    assert pagina.itens[1].disponibilidade.disponivel is False
    assert (pagina.total, pagina.page, pagina.page_size) == (7, 1, 2)


async def test_obra_sem_contagem_vira_indisponivel() -> None:
    """Se um exemplar for baixado entre as duas consultas, a obra não quebra o grid."""
    a = make_obra(id=uuid4())
    obra_repo, exemplar_repo = _build([a], 1, {})

    pagina = await ListarCatalogoPublicoUseCase(obra_repo, exemplar_repo).execute(None, 1, 20)

    assert pagina.itens[0].disponibilidade == DisponibilidadeObra(a.id, 0, 0)
