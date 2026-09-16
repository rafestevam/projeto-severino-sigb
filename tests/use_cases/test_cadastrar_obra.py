"""
Testes unitários para CadastrarObraUseCase.

Estratégia: usar unittest.mock.AsyncMock para mockar ObraRepository,
evitando qualquer dependência de banco de dados ou I/O externo.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.adapters.api.schemas.obra import ObraIn
from app.domain.entities.obra import Obra
from app.domain.exceptions import DuplicateIsbnError
from app.use_cases.cadastrar_obra import CadastrarObraUseCase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_obra_in(**overrides) -> ObraIn:
    defaults = {
        "isbn": "9788535902778",
        "titulo": "Dom Casmurro",
        "autores": ["Machado de Assis"],
        "editora": "Ática",
        "ano": 1899,
        "categoria": "Literatura Brasileira",
        "capa_url": None,
    }
    return ObraIn(**{**defaults, **overrides})


def _make_obra_entity(dados: ObraIn) -> Obra:
    return Obra(
        id=uuid4(),
        isbn=dados.isbn,
        titulo=dados.titulo,
        autores=dados.autores,
        editora=dados.editora,
        ano=dados.ano,
        capa_url=dados.capa_url,
        categoria=dados.categoria,
        created_at=datetime(2024, 1, 1),
    )


def _build_repo(*, existing_isbn: Obra | None = None) -> MagicMock:
    """Build a mock ObraRepository."""
    repo = MagicMock()
    repo.get_by_isbn = AsyncMock(return_value=existing_isbn)
    repo.save = AsyncMock(side_effect=lambda obra: obra)
    return repo


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


async def test_execute_cria_e_persiste_obra():
    """Obra com ISBN válido é criada e salva com sucesso."""
    dados = _make_obra_in()
    repo = _build_repo(existing_isbn=None)
    use_case = CadastrarObraUseCase(repo)

    result = await use_case.execute(dados)

    repo.get_by_isbn.assert_awaited_once_with(dados.isbn)
    repo.save.assert_awaited_once()
    assert result.titulo == dados.titulo
    assert result.isbn == dados.isbn


async def test_execute_cria_obra_sem_isbn():
    """Obra sem ISBN não aciona verificação de duplicidade e é salva normalmente."""
    dados = _make_obra_in(isbn=None)
    repo = _build_repo()
    use_case = CadastrarObraUseCase(repo)

    result = await use_case.execute(dados)

    repo.get_by_isbn.assert_not_called()
    repo.save.assert_awaited_once()
    assert result.isbn is None


async def test_execute_levanta_duplicate_isbn_error():
    """ISBN já existente no repositório causa DuplicateIsbnError."""
    dados = _make_obra_in()
    existing = _make_obra_entity(dados)
    repo = _build_repo(existing_isbn=existing)
    use_case = CadastrarObraUseCase(repo)

    with pytest.raises(DuplicateIsbnError) as exc_info:
        await use_case.execute(dados)

    assert exc_info.value.isbn == dados.isbn
    repo.save.assert_not_called()


async def test_execute_obra_tem_id_gerado():
    """A obra retornada possui um UUID gerado automaticamente."""
    dados = _make_obra_in()
    repo = _build_repo(existing_isbn=None)
    use_case = CadastrarObraUseCase(repo)

    result = await use_case.execute(dados)

    assert result.id is not None


async def test_execute_preserva_todos_os_campos():
    """Todos os campos do ObraIn são mapeados corretamente para a entidade."""
    dados = _make_obra_in(
        isbn="9788535902778",
        titulo="Dom Casmurro",
        autores=["Machado de Assis"],
        editora="Ática",
        ano=1899,
        categoria="Literatura Brasileira",
        capa_url="https://example.com/capa.jpg",
    )
    repo = _build_repo(existing_isbn=None)
    use_case = CadastrarObraUseCase(repo)

    result = await use_case.execute(dados)

    assert result.titulo == "Dom Casmurro"
    assert result.autores == ["Machado de Assis"]
    assert result.editora == "Ática"
    assert result.ano == 1899
    assert result.categoria == "Literatura Brasileira"
    assert result.capa_url == "https://example.com/capa.jpg"
