"""
Testes unitários para BuscarMetadadosIsbnUseCase.

Estratégia: usar unittest.mock.AsyncMock para mockar IsbnGateway,
evitando qualquer dependência de rede ou I/O externo.
O use case é um thin delegator — os testes verificam:
  - que o gateway é chamado com o ISBN correto;
  - que o resultado do gateway é repassado integralmente;
  - que None do gateway é substituído por IsbnMetadataOut() vazio.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.adapters.api.schemas.isbn_metadata import IsbnMetadataOut
from app.use_cases.buscar_metadados_isbn import BuscarMetadadosIsbnUseCase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_gateway(*, retorno: IsbnMetadataOut | None) -> MagicMock:
    """Constrói um mock de IsbnGateway com retorno configurado."""
    gateway = MagicMock()
    gateway.buscar = AsyncMock(return_value=retorno)
    return gateway


def _make_metadata(**kwargs) -> IsbnMetadataOut:
    defaults = {
        "titulo": "Dom Casmurro",
        "autores": ["Machado de Assis"],
        "editora": "Ática",
        "ano": 1899,
        "capa_url": "https://example.com/capa.jpg",
    }
    return IsbnMetadataOut(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Testes — delegação ao gateway
# ---------------------------------------------------------------------------


async def test_execute_chama_gateway_com_isbn_correto():
    """execute() deve delegar ao gateway passando exatamente o ISBN recebido."""
    isbn = "9788535902778"
    gateway = _build_gateway(retorno=_make_metadata())
    use_case = BuscarMetadadosIsbnUseCase(gateway)

    await use_case.execute(isbn)

    gateway.buscar.assert_awaited_once_with(isbn)


async def test_execute_retorna_resultado_do_gateway_quando_encontrado():
    """O resultado retornado pelo gateway deve ser propagado sem alteração."""
    metadata = _make_metadata(titulo="Dom Casmurro", ano=1899)
    gateway = _build_gateway(retorno=metadata)
    use_case = BuscarMetadadosIsbnUseCase(gateway)

    result = await use_case.execute("9788535902778")

    assert result is metadata


async def test_execute_retorna_schema_vazio_quando_gateway_retorna_none():
    """Quando o gateway retorna None, execute() deve retornar IsbnMetadataOut() vazio."""
    gateway = _build_gateway(retorno=None)
    use_case = BuscarMetadadosIsbnUseCase(gateway)

    result = await use_case.execute("0000000000000")

    assert isinstance(result, IsbnMetadataOut)
    assert result.titulo is None
    assert result.autores is None
    assert result.editora is None
    assert result.ano is None
    assert result.capa_url is None


async def test_execute_schema_vazio_tem_todos_campos_none():
    """O schema vazio retornado quando gateway dá None deve ter todos os campos None."""
    gateway = _build_gateway(retorno=None)
    use_case = BuscarMetadadosIsbnUseCase(gateway)

    result = await use_case.execute("9999999999999")

    for field in IsbnMetadataOut.model_fields:
        assert getattr(result, field) is None, f"Campo '{field}' deveria ser None"


# ---------------------------------------------------------------------------
# Testes — retorno com dados parciais
# ---------------------------------------------------------------------------


async def test_execute_retorna_metadata_com_apenas_titulo():
    """Metadata com apenas título preenchido deve ser repassada integralmente."""
    metadata = IsbnMetadataOut(titulo="Apenas Título")
    gateway = _build_gateway(retorno=metadata)
    use_case = BuscarMetadadosIsbnUseCase(gateway)

    result = await use_case.execute("9788535902778")

    assert result.titulo == "Apenas Título"
    assert result.autores is None
    assert result.editora is None
    assert result.ano is None
    assert result.capa_url is None


async def test_execute_retorna_metadata_completa():
    """Metadata totalmente preenchida deve ser repassada sem nenhuma modificação."""
    metadata = _make_metadata(
        titulo="Clean Code",
        autores=["Robert C. Martin"],
        editora="Prentice Hall",
        ano=2008,
        capa_url="https://example.com/clean-code.jpg",
    )
    gateway = _build_gateway(retorno=metadata)
    use_case = BuscarMetadadosIsbnUseCase(gateway)

    result = await use_case.execute("9780132350884")

    assert result.titulo == "Clean Code"
    assert result.autores == ["Robert C. Martin"]
    assert result.editora == "Prentice Hall"
    assert result.ano == 2008
    assert result.capa_url == "https://example.com/clean-code.jpg"


# ---------------------------------------------------------------------------
# Testes — ISBN 10 e múltiplos autores
# ---------------------------------------------------------------------------


async def test_execute_aceita_isbn10():
    """O use case deve aceitar e repassar ISBN-10 sem nenhuma transformação."""
    isbn10 = "0132350882"
    gateway = _build_gateway(retorno=IsbnMetadataOut(titulo="Qualquer"))
    use_case = BuscarMetadadosIsbnUseCase(gateway)

    await use_case.execute(isbn10)

    gateway.buscar.assert_awaited_once_with(isbn10)


async def test_execute_retorna_multiplos_autores():
    """Lista de múltiplos autores deve ser repassada sem truncamento."""
    metadata = IsbnMetadataOut(autores=["Autor A", "Autor B", "Autor C"])
    gateway = _build_gateway(retorno=metadata)
    use_case = BuscarMetadadosIsbnUseCase(gateway)

    result = await use_case.execute("9780000000001")

    assert result.autores == ["Autor A", "Autor B", "Autor C"]


# ---------------------------------------------------------------------------
# Testes — isolamento entre chamadas
# ---------------------------------------------------------------------------


async def test_gateway_chamado_uma_vez_por_execute():
    """Cada chamada a execute() deve acionar o gateway exatamente uma vez."""
    gateway = _build_gateway(retorno=None)
    use_case = BuscarMetadadosIsbnUseCase(gateway)

    await use_case.execute("9788535902778")
    await use_case.execute("9780132350884")

    assert gateway.buscar.await_count == 2
