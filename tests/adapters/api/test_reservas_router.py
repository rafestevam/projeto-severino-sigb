"""
Testes unitários para app/adapters/api/reservas.py (reservas_router).

Estratégia: sobrescrever get_db_session e get_current_user; mockar os use
cases dentro do módulo para isolamento total (sem banco de dados).

Cobre:
  - POST /api/reservas: 201 sucesso com posicao_fila, 400 leitor inativo,
    400 exemplar disponível, 409 reserva já existe, 401 sem token.
  - DELETE /api/reservas/{id}: 200 sucesso status expirada,
    404 reserva não encontrada, 401 sem token.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.api.deps import get_current_user
from app.domain.entities.reserva import Reserva
from app.domain.exceptions import (
    LeitorInativoError,
    ObraComExemplarDisponivelError,
    ReservaJaExisteError,
    ReservaNaoEncontradaError,
)
from app.infrastructure.database import get_db_session
from app.main import app

# ---------------------------------------------------------------------------
# Constantes e helpers
# ---------------------------------------------------------------------------

_RESERVA_ID = uuid4()
_OBRA_ID = uuid4()
_LEITOR_ID = uuid4()
_AUTH_HEADERS = {"Authorization": "Bearer test-token"}


def _make_reserva(status: str = "aguardando") -> Reserva:
    return Reserva(
        id=_RESERVA_ID,
        obra_id=_OBRA_ID,
        leitor_id=_LEITOR_ID,
        status=status,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def _fake_db_session() -> AsyncGenerator:
    mock_session = AsyncMock()
    yield mock_session


@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_current_user] = lambda: "test-user"
    app.dependency_overrides[get_db_session] = _fake_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture()
async def client_sem_auth() -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db_session] = _fake_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/reservas
# ---------------------------------------------------------------------------


class TestCriarReservaEndpoint:
    async def test_criar_reserva_sucesso_retorna_201(self, client: AsyncClient):
        import app.adapters.api.reservas as m

        orig = m.ReservarObraUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, obra_id, leitor_id): return _make_reserva(), 1

        m.ReservarObraUseCase = _Mock
        try:
            resp = await client.post(
                "/api/reservas",
                json={"obra_id": str(_OBRA_ID), "leitor_id": str(_LEITOR_ID)},
                headers=_AUTH_HEADERS,
            )
        finally:
            m.ReservarObraUseCase = orig

        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "aguardando"
        assert data["posicao_fila"] == 1
        assert data["obra_id"] == str(_OBRA_ID)
        assert data["leitor_id"] == str(_LEITOR_ID)

    async def test_criar_reserva_leitor_inativo_retorna_400(self, client: AsyncClient):
        import app.adapters.api.reservas as m

        orig = m.ReservarObraUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, obra_id, leitor_id):
                raise LeitorInativoError(str(leitor_id))

        m.ReservarObraUseCase = _Mock
        try:
            resp = await client.post(
                "/api/reservas",
                json={"obra_id": str(_OBRA_ID), "leitor_id": str(_LEITOR_ID)},
                headers=_AUTH_HEADERS,
            )
        finally:
            m.ReservarObraUseCase = orig

        assert resp.status_code == 400

    async def test_criar_reserva_exemplar_disponivel_retorna_400(self, client: AsyncClient):
        import app.adapters.api.reservas as m

        orig = m.ReservarObraUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, obra_id, leitor_id):
                raise ObraComExemplarDisponivelError(str(obra_id))

        m.ReservarObraUseCase = _Mock
        try:
            resp = await client.post(
                "/api/reservas",
                json={"obra_id": str(_OBRA_ID), "leitor_id": str(_LEITOR_ID)},
                headers=_AUTH_HEADERS,
            )
        finally:
            m.ReservarObraUseCase = orig

        assert resp.status_code == 400
        assert "disponível" in resp.json()["detail"]

    async def test_criar_reserva_ja_existente_retorna_409(self, client: AsyncClient):
        import app.adapters.api.reservas as m

        orig = m.ReservarObraUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, obra_id, leitor_id):
                raise ReservaJaExisteError(str(obra_id), str(leitor_id))

        m.ReservarObraUseCase = _Mock
        try:
            resp = await client.post(
                "/api/reservas",
                json={"obra_id": str(_OBRA_ID), "leitor_id": str(_LEITOR_ID)},
                headers=_AUTH_HEADERS,
            )
        finally:
            m.ReservarObraUseCase = orig

        assert resp.status_code == 409

    async def test_criar_reserva_sem_auth_retorna_401(self, client_sem_auth: AsyncClient):
        resp = await client_sem_auth.post(
            "/api/reservas",
            json={"obra_id": str(_OBRA_ID), "leitor_id": str(_LEITOR_ID)},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/reservas/{id}
# ---------------------------------------------------------------------------


class TestCancelarReservaEndpoint:
    async def test_cancelar_reserva_sucesso_retorna_200(self, client: AsyncClient):
        import app.adapters.api.reservas as m

        orig = m.CancelarReservaUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, reserva_id): return _make_reserva(status="expirada")

        m.CancelarReservaUseCase = _Mock
        try:
            resp = await client.delete(
                f"/api/reservas/{_RESERVA_ID}",
                headers=_AUTH_HEADERS,
            )
        finally:
            m.CancelarReservaUseCase = orig

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "expirada"
        assert data["id"] == str(_RESERVA_ID)

    async def test_cancelar_reserva_nao_encontrada_retorna_404(self, client: AsyncClient):
        import app.adapters.api.reservas as m

        orig = m.CancelarReservaUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, reserva_id):
                raise ReservaNaoEncontradaError(str(reserva_id))

        m.CancelarReservaUseCase = _Mock
        try:
            resp = await client.delete(
                f"/api/reservas/{_RESERVA_ID}",
                headers=_AUTH_HEADERS,
            )
        finally:
            m.CancelarReservaUseCase = orig

        assert resp.status_code == 404

    async def test_cancelar_reserva_sem_auth_retorna_401(self, client_sem_auth: AsyncClient):
        resp = await client_sem_auth.delete(f"/api/reservas/{_RESERVA_ID}")
        assert resp.status_code == 401
