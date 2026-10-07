"""
Testes unitários para app/adapters/api/exemplares.py (exemplares_router).

Estratégia: montar a FastAPI app com dependency overrides para get_db_session
e get_current_user, e mockar SQLAlchemyExemplarRepository e EtiquetaPdfService
para evitar qualquer dependência de banco de dados.

Cobre:
  - GET /api/exemplares/{codigo_qr}/etiqueta.pdf:
      - 200 com Content-Type: application/pdf quando exemplar existe.
      - 404 quando o código QR não é encontrado.
      - 401 sem token de autenticação.
      - O corpo da resposta começa com a assinatura %PDF.
  - GET /api/exemplares/by-qr/{codigo_qr}:
      - 200 com ExemplarOut enriquecido com titulo_obra quando exemplar existe.
      - 200 com titulo_obra=None quando obra não encontrada.
      - 404 quando código QR não é encontrado.
      - 401 sem token.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.api.deps import get_current_user
from app.domain.entities.exemplar import Exemplar
from app.domain.entities.obra import Obra
from app.infrastructure.database import get_db_session
from app.main import app


# ---------------------------------------------------------------------------
# Helpers — fábricas de entidades
# ---------------------------------------------------------------------------

def _make_exemplar(codigo_qr: str = "LIB-2025-00001") -> Exemplar:
    return Exemplar(
        id=uuid4(),
        obra_id=uuid4(),
        codigo_qr=codigo_qr,
        estado="disponivel",
        localizacao_estante="A-01",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def _make_obra(titulo: str = "Dom Casmurro") -> Obra:
    return Obra(
        id=uuid4(),
        isbn="9788535902778",
        titulo=titulo,
        autores=["Machado de Assis"],
        editora="Ática",
        ano=1899,
        capa_url=None,
        categoria="Literatura Brasileira",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


_AUTH_HEADERS = {"Authorization": "Bearer test-token"}

# PDF mínimo válido (apenas assinatura)
_FAKE_PDF = b"%PDF-1.4 fake content"


# ---------------------------------------------------------------------------
# Overrides de dependência
# ---------------------------------------------------------------------------

async def _fake_db_session() -> AsyncGenerator:
    yield MagicMock()


def _override_auth():
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
    _override_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    _clear_overrides()


# ---------------------------------------------------------------------------
# Helpers de mock do router
# ---------------------------------------------------------------------------

def _patch_repo_encontra(exemplar: Exemplar):
    """Substitui SQLAlchemyExemplarRepository por stub que retorna o exemplar."""
    import app.adapters.api.exemplares as m
    original = m.SQLAlchemyExemplarRepository

    class _MockRepo:
        def __init__(self, *args, **kwargs): pass
        async def get_by_codigo_qr(self, codigo_qr: str): return exemplar

    m.SQLAlchemyExemplarRepository = _MockRepo
    return original


def _patch_repo_nao_encontra():
    """Substitui SQLAlchemyExemplarRepository por stub que retorna None."""
    import app.adapters.api.exemplares as m
    original = m.SQLAlchemyExemplarRepository

    class _MockRepo:
        def __init__(self, *args, **kwargs): pass
        async def get_by_codigo_qr(self, codigo_qr: str): return None

    m.SQLAlchemyExemplarRepository = _MockRepo
    return original


def _patch_pdf_service(pdf_bytes: bytes = _FAKE_PDF):
    """Substitui EtiquetaPdfService por stub que retorna pdf_bytes."""
    import app.adapters.api.exemplares as m
    original = m.EtiquetaPdfService

    class _MockService:
        def gerar(self, exemplares): return pdf_bytes

    m.EtiquetaPdfService = _MockService
    return original


def _patch_obra_repo_encontra(obra: Obra | None):
    """Substitui SQLAlchemyObraRepository por stub que retorna a obra fornecida."""
    import app.adapters.api.exemplares as m
    original = m.SQLAlchemyObraRepository

    class _MockObraRepo:
        def __init__(self, *args, **kwargs): pass
        async def get_by_id(self, id): return obra

    m.SQLAlchemyObraRepository = _MockObraRepo
    return original


def _restore_repo(original):
    import app.adapters.api.exemplares as m
    m.SQLAlchemyExemplarRepository = original


def _restore_pdf(original):
    import app.adapters.api.exemplares as m
    m.EtiquetaPdfService = original


def _restore_obra_repo(original):
    import app.adapters.api.exemplares as m
    m.SQLAlchemyObraRepository = original


# ---------------------------------------------------------------------------
# GET /api/exemplares/{codigo_qr}/etiqueta.pdf
# ---------------------------------------------------------------------------


class TestGerarEtiquetaPdf:
    async def test_retorna_200_quando_exemplar_existe(self, client: AsyncClient):
        """GET /api/exemplares/{codigo_qr}/etiqueta.pdf retorna 200 para exemplar existente."""
        exemplar = _make_exemplar("LIB-2025-00001")
        orig_repo = _patch_repo_encontra(exemplar)
        orig_pdf = _patch_pdf_service()
        try:
            response = await client.get(
                "/api/exemplares/LIB-2025-00001/etiqueta.pdf",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig_repo)
            _restore_pdf(orig_pdf)

        assert response.status_code == 200

    async def test_content_type_e_application_pdf(self, client: AsyncClient):
        """A resposta deve ter Content-Type: application/pdf."""
        exemplar = _make_exemplar("LIB-2025-00001")
        orig_repo = _patch_repo_encontra(exemplar)
        orig_pdf = _patch_pdf_service()
        try:
            response = await client.get(
                "/api/exemplares/LIB-2025-00001/etiqueta.pdf",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig_repo)
            _restore_pdf(orig_pdf)

        assert response.headers["content-type"] == "application/pdf"

    async def test_body_comeca_com_assinatura_pdf(self, client: AsyncClient):
        """O corpo da resposta deve começar com %PDF."""
        exemplar = _make_exemplar("LIB-2025-00001")
        orig_repo = _patch_repo_encontra(exemplar)
        orig_pdf = _patch_pdf_service(_FAKE_PDF)
        try:
            response = await client.get(
                "/api/exemplares/LIB-2025-00001/etiqueta.pdf",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig_repo)
            _restore_pdf(orig_pdf)

        assert response.content.startswith(b"%PDF")

    async def test_retorna_404_quando_exemplar_nao_existe(self, client: AsyncClient):
        """GET /api/exemplares/{codigo_qr}/etiqueta.pdf retorna 404 para QR inexistente."""
        orig_repo = _patch_repo_nao_encontra()
        try:
            response = await client.get(
                "/api/exemplares/LIB-9999-99999/etiqueta.pdf",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig_repo)

        assert response.status_code == 404

    async def test_retorna_401_sem_token(self, client_sem_auth: AsyncClient):
        """GET /api/exemplares/{codigo_qr}/etiqueta.pdf sem token retorna 401."""
        response = await client_sem_auth.get(
            "/api/exemplares/LIB-2025-00001/etiqueta.pdf"
        )
        assert response.status_code == 401

    async def test_codigo_qr_com_hifens_e_aceito(self, client: AsyncClient):
        """Código QR com hífens (formato LIB-ANO-SEQ) deve ser aceito na URL."""
        exemplar = _make_exemplar("LIB-2025-00042")
        orig_repo = _patch_repo_encontra(exemplar)
        orig_pdf = _patch_pdf_service()
        try:
            response = await client.get(
                "/api/exemplares/LIB-2025-00042/etiqueta.pdf",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig_repo)
            _restore_pdf(orig_pdf)

        assert response.status_code == 200

    async def test_pdf_gerado_com_o_exemplar_correto(self, client: AsyncClient):
        """O serviço de PDF deve receber o exemplar encontrado pelo repositório."""
        exemplar = _make_exemplar("LIB-2025-00099")
        received_exemplares: list = []

        orig_repo = _patch_repo_encontra(exemplar)

        import app.adapters.api.exemplares as m
        orig_pdf = m.EtiquetaPdfService

        class _SpyService:
            def gerar(self, exemplares):
                received_exemplares.extend(exemplares)
                return _FAKE_PDF

        m.EtiquetaPdfService = _SpyService
        try:
            await client.get(
                "/api/exemplares/LIB-2025-00099/etiqueta.pdf",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig_repo)
            _restore_pdf(orig_pdf)

        assert len(received_exemplares) == 1
        assert received_exemplares[0].codigo_qr == "LIB-2025-00099"


# ---------------------------------------------------------------------------
# GET /api/exemplares/by-qr/{codigo_qr}
# ---------------------------------------------------------------------------


class TestObterExemplarPorQr:
    async def test_retorna_200_quando_exemplar_existe(self, client: AsyncClient):
        """GET /api/exemplares/by-qr/{codigo_qr} retorna 200 para exemplar existente."""
        exemplar = _make_exemplar("LIB-2025-00001")
        obra = _make_obra("Dom Casmurro")
        orig_repo = _patch_repo_encontra(exemplar)
        orig_obra = _patch_obra_repo_encontra(obra)
        try:
            response = await client.get(
                "/api/exemplares/by-qr/LIB-2025-00001",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig_repo)
            _restore_obra_repo(orig_obra)

        assert response.status_code == 200

    async def test_retorna_titulo_obra_enriquecido(self, client: AsyncClient):
        """GET /api/exemplares/by-qr/{codigo_qr} enriquece resposta com titulo_obra."""
        exemplar = _make_exemplar("LIB-2025-00001")
        obra = _make_obra("Dom Casmurro")
        orig_repo = _patch_repo_encontra(exemplar)
        orig_obra = _patch_obra_repo_encontra(obra)
        try:
            response = await client.get(
                "/api/exemplares/by-qr/LIB-2025-00001",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig_repo)
            _restore_obra_repo(orig_obra)

        data = response.json()
        assert data["titulo_obra"] == "Dom Casmurro"
        assert data["codigo_qr"] == "LIB-2025-00001"

    async def test_retorna_titulo_obra_none_quando_obra_nao_encontrada(
        self, client: AsyncClient
    ):
        """GET /api/exemplares/by-qr/{codigo_qr} retorna titulo_obra=None se obra ausente."""
        exemplar = _make_exemplar("LIB-2025-00001")
        orig_repo = _patch_repo_encontra(exemplar)
        orig_obra = _patch_obra_repo_encontra(None)
        try:
            response = await client.get(
                "/api/exemplares/by-qr/LIB-2025-00001",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig_repo)
            _restore_obra_repo(orig_obra)

        assert response.status_code == 200
        assert response.json()["titulo_obra"] is None

    async def test_retorna_404_quando_exemplar_nao_encontrado(self, client: AsyncClient):
        """GET /api/exemplares/by-qr/{codigo_qr} retorna 404 para QR inexistente."""
        orig_repo = _patch_repo_nao_encontra()
        try:
            response = await client.get(
                "/api/exemplares/by-qr/LIB-9999-99999",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig_repo)

        assert response.status_code == 404

    async def test_retorna_401_sem_token(self, client_sem_auth: AsyncClient):
        """GET /api/exemplares/by-qr/{codigo_qr} sem token retorna 401."""
        response = await client_sem_auth.get("/api/exemplares/by-qr/LIB-2025-00001")
        assert response.status_code == 401
