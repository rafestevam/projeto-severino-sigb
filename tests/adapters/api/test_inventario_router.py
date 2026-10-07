"""
Testes unitários para app/adapters/api/inventario.py (inventario_router).

Estratégia: sobrescrever dependências (get_db_session, get_current_user) com
stubs em memória e monkey-patching do use case — sem banco de dados nem rede.

Cobre:
  - POST /api/inventario/scan: 200 sucesso com as três listas.
  - POST /api/inventario/scan: 422 body inválido (sem localizacao).
  - POST /api/inventario/scan: 401 sem token.
"""
from __future__ import annotations

from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.api.deps import get_current_user
from app.infrastructure.database import get_db_session
from app.main import app
from app.use_cases.realizar_inventario import (
    ExemplarResumo,
    InventarioResultado,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AUTH_HEADERS = {"Authorization": "Bearer test-token-admin"}


async def _fake_db_session() -> AsyncGenerator:
    mock_session = AsyncMock()
    yield mock_session


def _override_auth():
    app.dependency_overrides[get_current_user] = lambda: "test-token-admin"


def _override_db():
    app.dependency_overrides[get_db_session] = _fake_db_session


def _clear_overrides():
    app.dependency_overrides.clear()


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
# POST /api/inventario/scan
# ---------------------------------------------------------------------------


class TestScanEndpoint:
    async def test_scan_sucesso_retorna_200(self, client: AsyncClient):
        import app.adapters.api.inventario as m

        resultado = InventarioResultado(
            encontrados=[ExemplarResumo(codigo_qr="QR-001", estado="disponivel")],
            nao_bipados=[],
            nao_esperados=[],
        )
        orig = m.RealizarInventarioUseCase

        class _Mock:
            def __init__(self, *a, **kw):
                pass

            async def execute(self, codigos_qr, localizacao, operador_keycloak_id):
                return resultado

        m.RealizarInventarioUseCase = _Mock
        try:
            resp = await client.post(
                "/api/inventario/scan",
                json={"codigos_qr": ["QR-001"], "localizacao": "A-01"},
                headers=_AUTH_HEADERS,
            )
        finally:
            m.RealizarInventarioUseCase = orig

        assert resp.status_code == 200
        data = resp.json()
        assert "encontrados" in data
        assert "nao_bipados" in data
        assert "nao_esperados" in data

    async def test_scan_retorna_encontrados_corretamente(self, client: AsyncClient):
        import app.adapters.api.inventario as m

        resultado = InventarioResultado(
            encontrados=[ExemplarResumo(codigo_qr="QR-001", estado="disponivel")],
            nao_bipados=[ExemplarResumo(codigo_qr="QR-002", estado="disponivel")],
            nao_esperados=[ExemplarResumo(codigo_qr="QR-003", estado="disponivel")],
        )
        orig = m.RealizarInventarioUseCase

        class _Mock:
            def __init__(self, *a, **kw):
                pass

            async def execute(self, codigos_qr, localizacao, operador_keycloak_id):
                return resultado

        m.RealizarInventarioUseCase = _Mock
        try:
            resp = await client.post(
                "/api/inventario/scan",
                json={"codigos_qr": ["QR-001", "QR-003"], "localizacao": "A-01"},
                headers=_AUTH_HEADERS,
            )
        finally:
            m.RealizarInventarioUseCase = orig

        data = resp.json()
        assert data["encontrados"][0]["codigo_qr"] == "QR-001"
        assert data["nao_bipados"][0]["codigo_qr"] == "QR-002"
        assert data["nao_esperados"][0]["codigo_qr"] == "QR-003"

    async def test_scan_body_invalido_sem_localizacao_retorna_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/inventario/scan",
            json={"codigos_qr": ["QR-001"]},  # falta localizacao
            headers=_AUTH_HEADERS,
        )
        assert resp.status_code == 422

    async def test_scan_sem_token_retorna_401(self, client_sem_auth: AsyncClient):
        resp = await client_sem_auth.post(
            "/api/inventario/scan",
            json={"codigos_qr": [], "localizacao": "A-01"},
        )
        assert resp.status_code == 401

    async def test_scan_lista_vazia_retorna_200(self, client: AsyncClient):
        import app.adapters.api.inventario as m

        resultado = InventarioResultado(
            encontrados=[],
            nao_bipados=[],
            nao_esperados=[],
        )
        orig = m.RealizarInventarioUseCase

        class _Mock:
            def __init__(self, *a, **kw):
                pass

            async def execute(self, codigos_qr, localizacao, operador_keycloak_id):
                return resultado

        m.RealizarInventarioUseCase = _Mock
        try:
            resp = await client.post(
                "/api/inventario/scan",
                json={"codigos_qr": [], "localizacao": "A-01"},
                headers=_AUTH_HEADERS,
            )
        finally:
            m.RealizarInventarioUseCase = orig

        assert resp.status_code == 200
        data = resp.json()
        assert data["encontrados"] == []
        assert data["nao_bipados"] == []
        assert data["nao_esperados"] == []
