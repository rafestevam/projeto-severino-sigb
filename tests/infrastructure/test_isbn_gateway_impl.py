"""
Testes unitários para IsbnGatewayImpl.

Estratégia: mockar httpx.AsyncClient com respostas controladas para cada
fonte (Open Library, Google Books, CBL), evitando qualquer I/O de rede.

Cobre:
  - Cascata: Open Library → Google Books → CBL (apenas se CBL_API_KEY definida)
  - Retorno imediato quando a primeira fonte encontra dados
  - Fallback para a próxima fonte quando a anterior falha ou não encontra
  - Retorno de None quando todas as fontes falham
  - Mapeamento correto de campos para cada fonte
  - Tratamento de httpx.HTTPError sem propagação de exceção
  - Lógica de CBL habilitada/desabilitada via env var
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.adapters.api.schemas.isbn_metadata import IsbnMetadataOut
from app.infrastructure.isbn_gateway_impl import IsbnGatewayImpl

_ISBN = "9788535902778"


# ---------------------------------------------------------------------------
# Fábrica de respostas httpx mockadas
# ---------------------------------------------------------------------------

def _make_response(*, status_code: int = 200, json_data: dict) -> MagicMock:
    """Constrói um mock de httpx.Response com json() e raise_for_status()."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=response,
        )
    else:
        response.raise_for_status.return_value = None
    return response


def _make_http_client(*, get_side_effects: list) -> MagicMock:
    """Cria um mock de httpx.AsyncClient cujos .get() retornam as respostas em sequência."""
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=get_side_effects)
    return client


# ---------------------------------------------------------------------------
# Payloads de resposta realistas por fonte
# ---------------------------------------------------------------------------

_OPEN_LIBRARY_HIT = {
    f"ISBN:{_ISBN}": {
        "title": "Dom Casmurro",
        "authors": [{"name": "Machado de Assis"}],
        "publishers": [{"name": "Ática"}],
        "publish_date": "1899",
        "cover": {
            "large": "https://covers.openlibrary.org/b/id/1-L.jpg",
            "medium": "https://covers.openlibrary.org/b/id/1-M.jpg",
        },
    }
}

_OPEN_LIBRARY_MISS = {}

_GOOGLE_BOOKS_HIT = {
    "items": [
        {
            "volumeInfo": {
                "title": "Dom Casmurro",
                "authors": ["Machado de Assis"],
                "publisher": "Ática",
                "publishedDate": "1899-01-01",
                "imageLinks": {
                    "thumbnail": "https://books.google.com/books/content?id=1&zoom=1",
                    "smallThumbnail": "https://books.google.com/books/content?id=1&zoom=5",
                },
            }
        }
    ]
}

_GOOGLE_BOOKS_MISS = {"totalItems": 0}

_CBL_HIT = {
    "value": [
        {
            "Title": "Dom Casmurro",
            "Authors": ["Machado de Assis"],
            "Publisher": "Ática",
            "Ano": "1899",
        }
    ]
}

_CBL_MISS = {"value": []}


# ---------------------------------------------------------------------------
# Testes — cascata de fontes
# ---------------------------------------------------------------------------


class TestCascata:
    async def test_retorna_open_library_quando_encontrado(self):
        """Se Open Library encontrar o ISBN, retorna imediatamente sem consultar as demais."""
        client = _make_http_client(
            get_side_effects=[_make_response(json_data=_OPEN_LIBRARY_HIT)]
        )
        gateway = IsbnGatewayImpl(client)

        result = await gateway.buscar(_ISBN)

        assert result is not None
        assert result.titulo == "Dom Casmurro"
        # Apenas 1 chamada HTTP — não consultou Google Books nem CBL
        assert client.get.await_count == 1

    async def test_fallback_para_google_books_quando_open_library_nao_encontra(self):
        """Quando Open Library retorna vazio, consulta Google Books."""
        client = _make_http_client(
            get_side_effects=[
                _make_response(json_data=_OPEN_LIBRARY_MISS),
                _make_response(json_data=_GOOGLE_BOOKS_HIT),
            ]
        )
        gateway = IsbnGatewayImpl(client)

        result = await gateway.buscar(_ISBN)

        assert result is not None
        assert result.titulo == "Dom Casmurro"
        assert client.get.await_count == 2

    async def test_fallback_para_google_books_quando_open_library_lanca_erro(self):
        """Quando Open Library levanta HTTPError, consulta Google Books."""
        client = _make_http_client(
            get_side_effects=[
                httpx.ConnectError("timeout"),
                _make_response(json_data=_GOOGLE_BOOKS_HIT),
            ]
        )
        gateway = IsbnGatewayImpl(client)

        result = await gateway.buscar(_ISBN)

        assert result is not None
        assert result.titulo == "Dom Casmurro"

    async def test_retorna_none_quando_todas_as_fontes_falham(self, monkeypatch):
        """Quando todas as fontes retornam vazio, buscar() retorna None."""
        monkeypatch.delenv("CBL_API_KEY", raising=False)
        client = _make_http_client(
            get_side_effects=[
                _make_response(json_data=_OPEN_LIBRARY_MISS),
                _make_response(json_data=_GOOGLE_BOOKS_MISS),
            ]
        )
        gateway = IsbnGatewayImpl(client)

        result = await gateway.buscar(_ISBN)

        assert result is None

    async def test_retorna_none_sem_lancar_excecao_quando_ambas_fontes_falham(
        self, monkeypatch
    ):
        """Falhas de rede em todas as fontes não devem propagar exceções."""
        monkeypatch.delenv("CBL_API_KEY", raising=False)
        client = _make_http_client(
            get_side_effects=[
                httpx.ConnectError("timeout ol"),
                httpx.ConnectError("timeout gb"),
            ]
        )
        gateway = IsbnGatewayImpl(client)

        result = await gateway.buscar(_ISBN)

        assert result is None

    async def test_consulta_cbl_quando_open_library_e_google_books_falham(
        self, monkeypatch
    ):
        """Com CBL_API_KEY definida e OL+GB falhando, deve consultar CBL."""
        monkeypatch.setenv("CBL_API_KEY", "test-key")
        client = _make_http_client(
            get_side_effects=[
                _make_response(json_data=_OPEN_LIBRARY_MISS),
                _make_response(json_data=_GOOGLE_BOOKS_MISS),
                _make_response(json_data=_CBL_HIT),
            ]
        )
        gateway = IsbnGatewayImpl(client)

        result = await gateway.buscar(_ISBN)

        assert result is not None
        assert result.titulo == "Dom Casmurro"
        assert client.get.await_count == 3

    async def test_nao_consulta_cbl_quando_env_var_nao_definida(self, monkeypatch):
        """Sem CBL_API_KEY, CBL não deve ser consultado mesmo com OL+GB falhando."""
        monkeypatch.delenv("CBL_API_KEY", raising=False)
        client = _make_http_client(
            get_side_effects=[
                _make_response(json_data=_OPEN_LIBRARY_MISS),
                _make_response(json_data=_GOOGLE_BOOKS_MISS),
            ]
        )
        gateway = IsbnGatewayImpl(client)

        result = await gateway.buscar(_ISBN)

        assert result is None
        # Apenas OL + Google Books consultados (2 chamadas)
        assert client.get.await_count == 2

    async def test_retorna_none_quando_cbl_disponivel_mas_tambem_nao_encontra(
        self, monkeypatch
    ):
        """Com todas as fontes retornando vazio (incluindo CBL), retorna None."""
        monkeypatch.setenv("CBL_API_KEY", "test-key")
        client = _make_http_client(
            get_side_effects=[
                _make_response(json_data=_OPEN_LIBRARY_MISS),
                _make_response(json_data=_GOOGLE_BOOKS_MISS),
                _make_response(json_data=_CBL_MISS),
            ]
        )
        gateway = IsbnGatewayImpl(client)

        result = await gateway.buscar(_ISBN)

        assert result is None


# ---------------------------------------------------------------------------
# Testes — mapeamento Open Library
# ---------------------------------------------------------------------------


class TestMapOpenLibrary:
    def test_mapeia_titulo(self):
        data = {"title": "Dom Casmurro"}
        result = IsbnGatewayImpl._map_open_library(data)
        assert result.titulo == "Dom Casmurro"

    def test_mapeia_autores_como_lista(self):
        data = {"authors": [{"name": "Machado de Assis"}, {"name": "Outro Autor"}]}
        result = IsbnGatewayImpl._map_open_library(data)
        assert result.autores == ["Machado de Assis", "Outro Autor"]

    def test_ignora_autores_sem_nome(self):
        data = {"authors": [{"name": "Autor Válido"}, {}]}
        result = IsbnGatewayImpl._map_open_library(data)
        assert result.autores == ["Autor Válido"]

    def test_autores_none_quando_campo_ausente(self):
        result = IsbnGatewayImpl._map_open_library({})
        assert result.autores is None

    def test_mapeia_editora_de_publishers_dict(self):
        data = {"publishers": [{"name": "Ática"}]}
        result = IsbnGatewayImpl._map_open_library(data)
        assert result.editora == "Ática"

    def test_mapeia_editora_de_publishers_string(self):
        data = {"publishers": ["Ática"]}
        result = IsbnGatewayImpl._map_open_library(data)
        assert result.editora == "Ática"

    def test_mapeia_ano_de_string_simples(self):
        data = {"publish_date": "1899"}
        result = IsbnGatewayImpl._map_open_library(data)
        assert result.ano == 1899

    def test_mapeia_ano_de_string_composta(self):
        data = {"publish_date": "Jan 2003"}
        result = IsbnGatewayImpl._map_open_library(data)
        assert result.ano == 2003

    def test_ano_none_quando_publish_date_ausente(self):
        result = IsbnGatewayImpl._map_open_library({})
        assert result.ano is None

    def test_mapeia_capa_url_preferindo_large(self):
        data = {
            "cover": {
                "large": "https://example.com/large.jpg",
                "medium": "https://example.com/medium.jpg",
            }
        }
        result = IsbnGatewayImpl._map_open_library(data)
        assert result.capa_url == "https://example.com/large.jpg"

    def test_mapeia_capa_url_fallback_medium(self):
        data = {"cover": {"medium": "https://example.com/medium.jpg"}}
        result = IsbnGatewayImpl._map_open_library(data)
        assert result.capa_url == "https://example.com/medium.jpg"

    def test_mapeia_capa_url_fallback_small(self):
        data = {"cover": {"small": "https://example.com/small.jpg"}}
        result = IsbnGatewayImpl._map_open_library(data)
        assert result.capa_url == "https://example.com/small.jpg"

    def test_capa_url_none_quando_cover_ausente(self):
        result = IsbnGatewayImpl._map_open_library({})
        assert result.capa_url is None

    def test_retorna_isbn_metadata_out(self):
        result = IsbnGatewayImpl._map_open_library({"title": "X"})
        assert isinstance(result, IsbnMetadataOut)


# ---------------------------------------------------------------------------
# Testes — mapeamento Google Books
# ---------------------------------------------------------------------------


class TestMapGoogleBooks:
    def test_mapeia_titulo(self):
        volume_info = {"title": "Clean Code"}
        result = IsbnGatewayImpl._map_google_books(volume_info)
        assert result.titulo == "Clean Code"

    def test_mapeia_autores(self):
        volume_info = {"authors": ["Robert C. Martin"]}
        result = IsbnGatewayImpl._map_google_books(volume_info)
        assert result.autores == ["Robert C. Martin"]

    def test_autores_none_quando_lista_vazia(self):
        volume_info = {"authors": []}
        result = IsbnGatewayImpl._map_google_books(volume_info)
        assert result.autores is None

    def test_autores_none_quando_campo_ausente(self):
        result = IsbnGatewayImpl._map_google_books({})
        assert result.autores is None

    def test_mapeia_editora(self):
        volume_info = {"publisher": "Prentice Hall"}
        result = IsbnGatewayImpl._map_google_books(volume_info)
        assert result.editora == "Prentice Hall"

    def test_mapeia_ano_de_data_iso(self):
        volume_info = {"publishedDate": "2008-08-11"}
        result = IsbnGatewayImpl._map_google_books(volume_info)
        assert result.ano == 2008

    def test_mapeia_ano_de_apenas_ano(self):
        volume_info = {"publishedDate": "2008"}
        result = IsbnGatewayImpl._map_google_books(volume_info)
        assert result.ano == 2008

    def test_ano_none_quando_published_date_ausente(self):
        result = IsbnGatewayImpl._map_google_books({})
        assert result.ano is None

    def test_mapeia_thumbnail(self):
        volume_info = {
            "imageLinks": {
                "thumbnail": "https://books.google.com/thumb.jpg",
                "smallThumbnail": "https://books.google.com/small.jpg",
            }
        }
        result = IsbnGatewayImpl._map_google_books(volume_info)
        assert result.capa_url == "https://books.google.com/thumb.jpg"

    def test_mapeia_small_thumbnail_quando_thumbnail_ausente(self):
        volume_info = {
            "imageLinks": {"smallThumbnail": "https://books.google.com/small.jpg"}
        }
        result = IsbnGatewayImpl._map_google_books(volume_info)
        assert result.capa_url == "https://books.google.com/small.jpg"

    def test_capa_url_none_quando_image_links_ausente(self):
        result = IsbnGatewayImpl._map_google_books({})
        assert result.capa_url is None

    def test_retorna_isbn_metadata_out(self):
        result = IsbnGatewayImpl._map_google_books({"title": "X"})
        assert isinstance(result, IsbnMetadataOut)


# ---------------------------------------------------------------------------
# Testes — mapeamento CBL
# ---------------------------------------------------------------------------


class TestMapCbl:
    def test_mapeia_titulo_campo_title(self):
        record = {"Title": "Dom Casmurro"}
        result = IsbnGatewayImpl._map_cbl(record)
        assert result.titulo == "Dom Casmurro"

    def test_mapeia_titulo_campo_title_minusculo(self):
        record = {"title": "Dom Casmurro"}
        result = IsbnGatewayImpl._map_cbl(record)
        assert result.titulo == "Dom Casmurro"

    def test_mapeia_autores_lista(self):
        record = {"Authors": ["Machado de Assis", "Outro"]}
        result = IsbnGatewayImpl._map_cbl(record)
        assert result.autores == ["Machado de Assis", "Outro"]

    def test_mapeia_autores_string_unica(self):
        record = {"Authors": "Machado de Assis"}
        result = IsbnGatewayImpl._map_cbl(record)
        assert result.autores == ["Machado de Assis"]

    def test_autores_none_quando_campo_ausente(self):
        result = IsbnGatewayImpl._map_cbl({})
        assert result.autores is None

    def test_mapeia_editora_campo_publisher(self):
        record = {"Publisher": "Ática"}
        result = IsbnGatewayImpl._map_cbl(record)
        assert result.editora == "Ática"

    def test_mapeia_editora_campo_publisher_minusculo(self):
        record = {"publisher": "Ática"}
        result = IsbnGatewayImpl._map_cbl(record)
        assert result.editora == "Ática"

    def test_mapeia_ano_campo_ano_maiusculo(self):
        record = {"Ano": "2003"}
        result = IsbnGatewayImpl._map_cbl(record)
        assert result.ano == 2003

    def test_mapeia_ano_campo_ano_minusculo(self):
        record = {"ano": "2003"}
        result = IsbnGatewayImpl._map_cbl(record)
        assert result.ano == 2003

    def test_ano_none_quando_campo_ausente(self):
        result = IsbnGatewayImpl._map_cbl({})
        assert result.ano is None

    def test_capa_url_sempre_none(self):
        """CBL não fornece URL de capa — deve ser sempre None."""
        record = {"Title": "Qualquer", "Authors": ["A"], "Publisher": "P", "Ano": "2000"}
        result = IsbnGatewayImpl._map_cbl(record)
        assert result.capa_url is None

    def test_retorna_isbn_metadata_out(self):
        result = IsbnGatewayImpl._map_cbl({"Title": "X"})
        assert isinstance(result, IsbnMetadataOut)


# ---------------------------------------------------------------------------
# Testes — tratamento de erros HTTP
# ---------------------------------------------------------------------------


class TestTratamentoErros:
    async def test_open_library_http_error_nao_propaga(self, monkeypatch):
        """HTTPError no Open Library deve ser tratado silenciosamente."""
        monkeypatch.delenv("CBL_API_KEY", raising=False)
        client = _make_http_client(
            get_side_effects=[
                httpx.ConnectError("timeout"),
                _make_response(json_data=_GOOGLE_BOOKS_MISS),
            ]
        )
        gateway = IsbnGatewayImpl(client)

        result = await gateway.buscar(_ISBN)  # não deve levantar exceção

        assert result is None

    async def test_google_books_http_error_nao_propaga(self, monkeypatch):
        """HTTPError no Google Books deve ser tratado silenciosamente."""
        monkeypatch.delenv("CBL_API_KEY", raising=False)
        client = _make_http_client(
            get_side_effects=[
                _make_response(json_data=_OPEN_LIBRARY_MISS),
                httpx.ConnectError("timeout"),
            ]
        )
        gateway = IsbnGatewayImpl(client)

        result = await gateway.buscar(_ISBN)

        assert result is None

    async def test_cbl_http_error_nao_propaga(self, monkeypatch):
        """HTTPError no CBL deve ser tratado silenciosamente."""
        monkeypatch.setenv("CBL_API_KEY", "test-key")
        client = _make_http_client(
            get_side_effects=[
                _make_response(json_data=_OPEN_LIBRARY_MISS),
                _make_response(json_data=_GOOGLE_BOOKS_MISS),
                httpx.ConnectError("timeout"),
            ]
        )
        gateway = IsbnGatewayImpl(client)

        result = await gateway.buscar(_ISBN)

        assert result is None

    async def test_status_4xx_tratado_sem_propagacao(self, monkeypatch):
        """Resposta HTTP 4xx deve ser tratada como falha, sem propagar exceção."""
        monkeypatch.delenv("CBL_API_KEY", raising=False)
        client = _make_http_client(
            get_side_effects=[
                _make_response(status_code=404, json_data={}),
                _make_response(json_data=_GOOGLE_BOOKS_MISS),
            ]
        )
        gateway = IsbnGatewayImpl(client)

        result = await gateway.buscar(_ISBN)

        assert result is None
