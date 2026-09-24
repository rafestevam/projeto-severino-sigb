"""
Testes unitários para app/adapters/api/admin.py (admin_router).

Estratégia: montar a FastAPI app, sobrescrever dependências
(get_db_session, get_current_user) com stubs em memória que não tocam
banco de dados real.

Cobre:
  - GET /api/admin/configuracao: 200 listagem de configurações, 401 sem token.
  - PUT /api/admin/configuracao/{chave}: 200 atualizar existente, 200 criar nova, 401 sem token.
"""
from __future__ import annotations

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.api.deps import get_current_user
from app.adapters.repositories.models.configuracao import ConfiguracaoModel
from app.infrastructure.database import get_db_session
from app.main import app

_AUTH_HEADERS = {"Authorization": "Bearer test-admin-token"}


@pytest.fixture()
def mock_session():
    mock = AsyncMock()
    mock.add = MagicMock()
    return mock


@pytest.fixture()
async def client(mock_session) -> AsyncGenerator[AsyncClient, None]:
    async def _fake_session():
        yield mock_session

    app.dependency_overrides[get_current_user] = lambda: "admin-user"
    app.dependency_overrides[get_db_session] = _fake_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture()
async def client_sem_auth(mock_session) -> AsyncGenerator[AsyncClient, None]:
    async def _fake_session():
        yield mock_session

    app.dependency_overrides[get_db_session] = _fake_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


class TestListarConfiguracoes:
    async def test_listar_retorna_200_com_items(self, client: AsyncClient, mock_session: AsyncMock):
        item1 = ConfiguracaoModel(id=uuid4(), chave="dias_emprestimo", valor="14")
        item2 = ConfiguracaoModel(id=uuid4(), chave="max_renovacoes", valor="3")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [item1, item2]
        mock_session.execute.return_value = mock_result

        resp = await client.get("/api/admin/configuracao", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) == 2
        assert data["items"][0]["chave"] == "dias_emprestimo"
        assert data["items"][0]["valor"] == "14"

    async def test_listar_sem_auth_retorna_401(self, client_sem_auth: AsyncClient):
        resp = await client_sem_auth.get("/api/admin/configuracao")
        assert resp.status_code == 401


class TestAtualizarConfiguracao:
    async def test_atualizar_existente_retorna_200(self, client: AsyncClient, mock_session: AsyncMock):
        existing = ConfiguracaoModel(id=uuid4(), chave="dias_emprestimo", valor="14")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        resp = await client.put(
            "/api/admin/configuracao/dias_emprestimo",
            json={"valor": "21"},
            headers=_AUTH_HEADERS,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["chave"] == "dias_emprestimo"
        assert data["valor"] == "21"
        mock_session.commit.assert_awaited_once()

    async def test_criar_nova_configuracao_retorna_200(self, client: AsyncClient, mock_session: AsyncMock):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        resp = await client.put(
            "/api/admin/configuracao/nova_chave",
            json={"valor": "100"},
            headers=_AUTH_HEADERS,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["chave"] == "nova_chave"
        assert data["valor"] == "100"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    async def test_atualizar_sem_auth_retorna_401(self, client_sem_auth: AsyncClient):
        resp = await client_sem_auth.put(
            "/api/admin/configuracao/dias_emprestimo",
            json={"valor": "21"},
        )
        assert resp.status_code == 401
