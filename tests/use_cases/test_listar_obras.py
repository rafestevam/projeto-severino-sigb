"""
Testes unitários para ListarObrasUseCase.

Estratégia: usar unittest.mock.AsyncMock para mockar ObraRepository,
evitando qualquer dependência de banco de dados ou I/O externo.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.entities.obra import Obra
from app.use_cases.listar_obras import ListarObrasUseCase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_obra(titulo: str = "Dom Casmurro", categoria: str = "Literatura Brasileira") -> Obra:
    return Obra(
        id=uuid4(),
        isbn="9788535902778",
        titulo=titulo,
        autores=["Machado de Assis"],
        editora="Ática",
        ano=1899,
        capa_url=None,
        categoria=categoria,
        created_at=datetime(2024, 1, 1),
    )


def _build_repo(obras: list[Obra], total: int | None = None) -> MagicMock:
    """Build a mock ObraRepository where list_filtered returns (obras, total)."""
    repo = MagicMock()
    repo.list_filtered = AsyncMock(return_value=(obras, total if total is not None else len(obras)))
    return repo


# ---------------------------------------------------------------------------
# Testes de delegação e valores padrão
# ---------------------------------------------------------------------------


async def test_execute_delega_para_list_filtered():
    """execute() deve chamar repo.list_filtered com os parâmetros recebidos."""
    obra = _make_obra()
    repo = _build_repo([obra])
    use_case = ListarObrasUseCase(repo)

    await use_case.execute(titulo="Dom", autor="Machado", categoria="Literatura Brasileira", page=2, page_size=10)

    repo.list_filtered.assert_awaited_once_with(
        titulo="Dom",
        autor="Machado",
        categoria="Literatura Brasileira",
        page=2,
        page_size=10,
    )


async def test_execute_usa_valores_padrao():
    """Sem argumentos, execute() usa page=1 e page_size=20."""
    repo = _build_repo([])
    use_case = ListarObrasUseCase(repo)

    await use_case.execute()

    repo.list_filtered.assert_awaited_once_with(
        titulo=None,
        autor=None,
        categoria=None,
        page=1,
        page_size=20,
    )


# ---------------------------------------------------------------------------
# Testes de retorno
# ---------------------------------------------------------------------------


async def test_execute_retorna_tupla_obras_e_total():
    """O retorno é exatamente o que o repositório devolveu: (list[Obra], int)."""
    obras = [_make_obra("Dom Casmurro"), _make_obra("Memórias Póstumas")]
    repo = _build_repo(obras, total=42)
    use_case = ListarObrasUseCase(repo)

    result_obras, result_total = await use_case.execute()

    assert result_obras == obras
    assert result_total == 42


async def test_execute_retorna_lista_vazia_quando_nao_ha_obras():
    """Lista vazia e total 0 são retornados quando o repositório não encontra obras."""
    repo = _build_repo([], total=0)
    use_case = ListarObrasUseCase(repo)

    result_obras, result_total = await use_case.execute()

    assert result_obras == []
    assert result_total == 0


async def test_execute_retorna_obra_unica():
    """Uma lista com um único resultado é devolvida sem transformação."""
    obra = _make_obra()
    repo = _build_repo([obra], total=1)
    use_case = ListarObrasUseCase(repo)

    result_obras, result_total = await use_case.execute()

    assert len(result_obras) == 1
    assert result_obras[0] is obra
    assert result_total == 1


# ---------------------------------------------------------------------------
# Testes de filtros individuais
# ---------------------------------------------------------------------------


async def test_execute_com_filtro_titulo():
    """Filtro por título é passado ao repositório e None é usado para os demais."""
    repo = _build_repo([])
    use_case = ListarObrasUseCase(repo)

    await use_case.execute(titulo="Dom")

    repo.list_filtered.assert_awaited_once_with(
        titulo="Dom",
        autor=None,
        categoria=None,
        page=1,
        page_size=20,
    )


async def test_execute_com_filtro_autor():
    """Filtro por autor é passado ao repositório com os demais como None."""
    repo = _build_repo([])
    use_case = ListarObrasUseCase(repo)

    await use_case.execute(autor="Machado")

    repo.list_filtered.assert_awaited_once_with(
        titulo=None,
        autor="Machado",
        categoria=None,
        page=1,
        page_size=20,
    )


async def test_execute_com_filtro_categoria():
    """Filtro por categoria é passado ao repositório com os demais como None."""
    repo = _build_repo([])
    use_case = ListarObrasUseCase(repo)

    await use_case.execute(categoria="Ficção")

    repo.list_filtered.assert_awaited_once_with(
        titulo=None,
        autor=None,
        categoria="Ficção",
        page=1,
        page_size=20,
    )
