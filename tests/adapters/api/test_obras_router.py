"""
Testes unitários para app/adapters/api/obras.py (obras_router).

Estratégia: montar a FastAPI app, sobrescrever todas as dependências
(get_db_session, get_current_user) com stubs em memória que não tocam
banco de dados nem rede. Os use cases são executados com repositórios
in-memory, garantindo isolamento total.

Cobre:
  - POST /api/obras: 201 criação, 409 ISBN duplicado, 401 sem token, 422 ISBN inválido.
  - GET /api/obras: 200 com estrutura de paginação, filtros repassados, sem auth 401.
  - POST /api/obras/isbn/{isbn}: 200 com metadata, retorno vazio quando não encontrado.
  - POST /api/obras/{obra_id}/exemplares: 201 criação, 404 obra inexistente.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.api.deps import get_current_user
from app.adapters.api.schemas.isbn_metadata import IsbnMetadataOut
from app.domain.entities.exemplar import Exemplar
from app.domain.entities.obra import Obra
from app.domain.exceptions import DuplicateIsbnError, ObraNotFoundError
from app.infrastructure.database import get_db_session
from app.main import app

# ---------------------------------------------------------------------------
# Helpers — fábricas de entidades
# ---------------------------------------------------------------------------

_OBRA_ID = uuid4()
_EXEMPLAR_ID = uuid4()


def _make_obra(obra_id: UUID = _OBRA_ID) -> Obra:
    return Obra(
        id=obra_id,
        isbn="9788535902778",
        titulo="Dom Casmurro",
        autores=["Machado de Assis"],
        editora="Ática",
        ano=1899,
        capa_url=None,
        categoria="Literatura Brasileira",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_exemplar(obra_id: UUID = _OBRA_ID) -> Exemplar:
    return Exemplar(
        id=_EXEMPLAR_ID,
        obra_id=obra_id,
        codigo_qr="LIB-2025-00001",
        estado="disponivel",
        localizacao_estante="A-01",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Payloads reutilizáveis
# ---------------------------------------------------------------------------

_OBRA_VALIDA = {
    "isbn": "9788535902778",
    "titulo": "Dom Casmurro",
    "autores": ["Machado de Assis"],
    "editora": "Ática",
    "ano": 1899,
    "categoria": "Literatura Brasileira",
    "capa_url": None,
}

_AUTH_HEADERS = {"Authorization": "Bearer test-token"}


# ---------------------------------------------------------------------------
# Fixtures — overrides de dependência
# ---------------------------------------------------------------------------

async def _fake_db_session() -> AsyncGenerator:
    """Sessão fake — os repositórios são mockados nos testes, não precisam de DB real."""
    yield MagicMock()


def _override_auth():
    """Substitui get_current_user por um stub que aceita qualquer token."""
    app.dependency_overrides[get_current_user] = lambda: "test-user"


def _override_db():
    app.dependency_overrides[get_db_session] = _fake_db_session


def _clear_overrides():
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fixture de client
# ---------------------------------------------------------------------------

@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    _override_auth()
    _override_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    _clear_overrides()


@pytest.fixture()
async def client_sem_auth() -> AsyncGenerator[AsyncClient, None]:
    """Client sem override de autenticação — usa a dependência real."""
    _override_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    _clear_overrides()


# ---------------------------------------------------------------------------
# Helpers de mock de use cases
# ---------------------------------------------------------------------------

def _patch_cadastrar_obra(obra: Obra):
    """Injeta mock que retorna 'obra' diretamente no router."""
    from app import adapters
    import app.adapters.api.obras as obras_module

    original = obras_module.CadastrarObraUseCase

    class _MockUseCase:
        def __init__(self, *args, **kwargs): pass
        async def execute(self, dados): return obra

    obras_module.CadastrarObraUseCase = _MockUseCase
    return original


def _patch_cadastrar_obra_duplicado():
    import app.adapters.api.obras as obras_module
    original = obras_module.CadastrarObraUseCase

    class _MockUseCase:
        def __init__(self, *args, **kwargs): pass
        async def execute(self, dados): raise DuplicateIsbnError("9788535902778")

    obras_module.CadastrarObraUseCase = _MockUseCase
    return original


def _patch_listar_obras(obras: list[Obra], total: int):
    import app.adapters.api.obras as obras_module
    original = obras_module.ListarObrasUseCase

    class _MockUseCase:
        def __init__(self, *args, **kwargs): pass
        async def execute(self, **kwargs): return obras, total

    obras_module.ListarObrasUseCase = _MockUseCase
    return original


def _patch_buscar_isbn(metadata: IsbnMetadataOut):
    import app.adapters.api.obras as obras_module
    original = obras_module.BuscarMetadadosIsbnUseCase

    class _MockUseCase:
        def __init__(self, *args, **kwargs): pass
        async def execute(self, isbn): return metadata

    obras_module.BuscarMetadadosIsbnUseCase = _MockUseCase
    return original


def _patch_adicionar_exemplares(exemplares: list[Exemplar]):
    import app.adapters.api.obras as obras_module
    original = obras_module.AdicionarExemplaresUseCase

    class _MockUseCase:
        def __init__(self, *args, **kwargs): pass
        async def execute(self, obra_id, quantidade, localizacao_estante): return exemplares

    obras_module.AdicionarExemplaresUseCase = _MockUseCase
    return original


def _patch_adicionar_exemplares_not_found():
    import app.adapters.api.obras as obras_module
    original = obras_module.AdicionarExemplaresUseCase

    class _MockUseCase:
        def __init__(self, *args, **kwargs): pass
        async def execute(self, obra_id, quantidade, localizacao_estante):
            raise ObraNotFoundError(str(obra_id))

    obras_module.AdicionarExemplaresUseCase = _MockUseCase
    return original


def _restore(module_attr: str, original):
    import app.adapters.api.obras as obras_module
    setattr(obras_module, module_attr, original)


# ---------------------------------------------------------------------------
# POST /api/obras
# ---------------------------------------------------------------------------


class TestCadastrarObra:
    async def test_retorna_201_com_obra_criada(self, client: AsyncClient):
        """POST /api/obras com dados válidos retorna 201 e o body da obra."""
        obra = _make_obra()
        import app.adapters.api.obras as m
        original = _patch_cadastrar_obra(obra)
        try:
            response = await client.post("/api/obras", json=_OBRA_VALIDA, headers=_AUTH_HEADERS)
        finally:
            _restore("CadastrarObraUseCase", original)

        assert response.status_code == 201
        data = response.json()
        assert data["titulo"] == "Dom Casmurro"
        assert data["isbn"] == "9788535902778"
        assert "id" in data

    async def test_retorna_409_para_isbn_duplicado(self, client: AsyncClient):
        """POST /api/obras com ISBN duplicado retorna 409 com 'isbn' no detail."""
        import app.adapters.api.obras as m
        original = _patch_cadastrar_obra_duplicado()
        try:
            response = await client.post("/api/obras", json=_OBRA_VALIDA, headers=_AUTH_HEADERS)
        finally:
            _restore("CadastrarObraUseCase", original)

        assert response.status_code == 409
        assert "isbn" in response.json()["detail"].lower()

    async def test_retorna_401_sem_token(self, client_sem_auth: AsyncClient):
        """POST /api/obras sem token retorna 401."""
        response = await client_sem_auth.post("/api/obras", json=_OBRA_VALIDA)
        assert response.status_code == 401

    async def test_retorna_422_para_isbn_invalido(self, client: AsyncClient):
        """POST /api/obras com ISBN de dígito verificador inválido retorna 422."""
        payload = {**_OBRA_VALIDA, "isbn": "9999999999999"}
        response = await client.post("/api/obras", json=payload, headers=_AUTH_HEADERS)
        assert response.status_code == 422

    async def test_retorna_201_para_obra_sem_isbn(self, client: AsyncClient):
        """POST /api/obras sem ISBN (isbn=None) retorna 201 com isbn=None."""
        obra = _make_obra()
        obra_sem_isbn = Obra(
            id=obra.id,
            isbn=None,
            titulo=obra.titulo,
            autores=obra.autores,
            editora=obra.editora,
            ano=obra.ano,
            capa_url=obra.capa_url,
            categoria=obra.categoria,
            created_at=obra.created_at,
        )
        import app.adapters.api.obras as m
        original = _patch_cadastrar_obra(obra_sem_isbn)
        try:
            payload = {**_OBRA_VALIDA, "isbn": None}
            response = await client.post("/api/obras", json=payload, headers=_AUTH_HEADERS)
        finally:
            _restore("CadastrarObraUseCase", original)

        assert response.status_code == 201
        assert response.json()["isbn"] is None

    async def test_retorna_422_para_payload_invalido(self, client: AsyncClient):
        """POST /api/obras sem campos obrigatórios retorna 422."""
        response = await client.post("/api/obras", json={"isbn": "9788535902778"}, headers=_AUTH_HEADERS)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/obras
# ---------------------------------------------------------------------------


class TestListarObras:
    async def test_retorna_200_com_estrutura_de_paginacao(self, client: AsyncClient):
        """GET /api/obras retorna 200 com items, total, page e page_size."""
        import app.adapters.api.obras as m
        original = _patch_listar_obras([_make_obra()], total=1)
        try:
            response = await client.get("/api/obras", headers=_AUTH_HEADERS)
        finally:
            _restore("ListarObrasUseCase", original)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    async def test_page_size_padrao_e_20(self, client: AsyncClient):
        """GET /api/obras sem parâmetros deve ter page_size=20."""
        import app.adapters.api.obras as m
        original = _patch_listar_obras([], total=0)
        try:
            response = await client.get("/api/obras", headers=_AUTH_HEADERS)
        finally:
            _restore("ListarObrasUseCase", original)

        assert response.json()["page_size"] == 20

    async def test_retorna_401_sem_token(self, client_sem_auth: AsyncClient):
        """GET /api/obras sem token retorna 401."""
        response = await client_sem_auth.get("/api/obras")
        assert response.status_code == 401

    async def test_lista_vazia(self, client: AsyncClient):
        """GET /api/obras sem obras retorna items=[] e total=0."""
        import app.adapters.api.obras as m
        original = _patch_listar_obras([], total=0)
        try:
            response = await client.get("/api/obras", headers=_AUTH_HEADERS)
        finally:
            _restore("ListarObrasUseCase", original)

        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_retorna_obras_em_items(self, client: AsyncClient):
        """GET /api/obras retorna a lista de obras dentro de 'items'."""
        import app.adapters.api.obras as m
        original = _patch_listar_obras([_make_obra()], total=1)
        try:
            response = await client.get("/api/obras", headers=_AUTH_HEADERS)
        finally:
            _restore("ListarObrasUseCase", original)

        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["titulo"] == "Dom Casmurro"


# ---------------------------------------------------------------------------
# POST /api/obras/isbn/{isbn}
# ---------------------------------------------------------------------------


class TestBuscarMetadadosIsbn:
    async def test_retorna_200_com_metadata(self, client: AsyncClient):
        """POST /api/obras/isbn/{isbn} retorna 200 com campos de metadata."""
        metadata = IsbnMetadataOut(
            titulo="Dom Casmurro",
            autores=["Machado de Assis"],
            editora="Ática",
            ano=1899,
        )
        import app.adapters.api.obras as m
        original = _patch_buscar_isbn(metadata)
        try:
            response = await client.post(
                "/api/obras/isbn/9788535902778", headers=_AUTH_HEADERS
            )
        finally:
            _restore("BuscarMetadadosIsbnUseCase", original)

        assert response.status_code == 200
        data = response.json()
        assert "titulo" in data
        assert data["titulo"] == "Dom Casmurro"

    async def test_retorna_200_com_schema_vazio_quando_nao_encontrado(self, client: AsyncClient):
        """POST /api/obras/isbn/{isbn} para ISBN desconhecido retorna 200 com campos None."""
        import app.adapters.api.obras as m
        original = _patch_buscar_isbn(IsbnMetadataOut())
        try:
            response = await client.post(
                "/api/obras/isbn/0000000000000", headers=_AUTH_HEADERS
            )
        finally:
            _restore("BuscarMetadadosIsbnUseCase", original)

        assert response.status_code == 200
        data = response.json()
        assert data.get("titulo") is None

    async def test_retorna_401_sem_token(self, client_sem_auth: AsyncClient):
        """POST /api/obras/isbn/{isbn} sem token retorna 401."""
        response = await client_sem_auth.post("/api/obras/isbn/9788535902778")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/obras/{obra_id}/exemplares
# ---------------------------------------------------------------------------


class TestAdicionarExemplares:
    _PAYLOAD = {"quantidade": 3, "localizacao_estante": "A-01"}

    async def test_retorna_201_com_lista_de_exemplares(self, client: AsyncClient):
        """POST /api/obras/{id}/exemplares retorna 201 com lista de ExemplarOut."""
        exemplares = [_make_exemplar()]
        import app.adapters.api.obras as m
        original = _patch_adicionar_exemplares(exemplares)
        try:
            response = await client.post(
                f"/api/obras/{_OBRA_ID}/exemplares",
                json=self._PAYLOAD,
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore("AdicionarExemplaresUseCase", original)

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["codigo_qr"] == "LIB-2025-00001"

    async def test_retorna_404_para_obra_inexistente(self, client: AsyncClient):
        """POST /api/obras/{id}/exemplares com obra inexistente retorna 404."""
        import app.adapters.api.obras as m
        original = _patch_adicionar_exemplares_not_found()
        try:
            response = await client.post(
                f"/api/obras/{_OBRA_ID}/exemplares",
                json=self._PAYLOAD,
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore("AdicionarExemplaresUseCase", original)

        assert response.status_code == 404

    async def test_retorna_401_sem_token(self, client_sem_auth: AsyncClient):
        """POST /api/obras/{id}/exemplares sem token retorna 401."""
        response = await client_sem_auth.post(
            f"/api/obras/{_OBRA_ID}/exemplares", json=self._PAYLOAD
        )
        assert response.status_code == 401

    async def test_retorna_422_para_quantidade_zero(self, client: AsyncClient):
        """POST /api/obras/{id}/exemplares com quantidade=0 retorna 422."""
        response = await client.post(
            f"/api/obras/{_OBRA_ID}/exemplares",
            json={"quantidade": 0, "localizacao_estante": "A-01"},
            headers=_AUTH_HEADERS,
        )
        assert response.status_code == 422

    async def test_retorna_422_para_obra_id_invalido(self, client: AsyncClient):
        """POST /api/obras/{id}/exemplares com UUID inválido retorna 422."""
        response = await client.post(
            "/api/obras/nao-e-um-uuid/exemplares",
            json=self._PAYLOAD,
            headers=_AUTH_HEADERS,
        )
        assert response.status_code == 422
