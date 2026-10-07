"""
Testes unitários para app/adapters/api/leitores.py (leitores_router).

Estratégia: montar a FastAPI app com dependency overrides para get_db_session
e get_current_user, e monkeypatch SQLAlchemyLeitorRepository para evitar
qualquer dependência de banco de dados.

Cobre:
  - GET /api/leitores?cpf={cpf}:
      - 200 com LeitorOut quando leitor existe.
      - 404 quando CPF não é encontrado.
      - 401 sem token de autenticação.
      - O hash SHA-256 é calculado corretamente antes da consulta ao repositório.
      - Leitor inativo retorna 200 com ativo=False.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.api.deps import get_current_user
from app.domain.entities.leitor import Leitor
from app.infrastructure.database import get_db_session
from app.main import app


# ---------------------------------------------------------------------------
# Helpers — fábricas de entidades
# ---------------------------------------------------------------------------

def _make_leitor(nome: str = "João Silva", ativo: bool = True) -> Leitor:
    return Leitor(
        id=uuid4(),
        nome=nome,
        cpf_hash=hashlib.sha256("12345678901".encode()).hexdigest(),
        telefone="11999999999",
        email="joao@example.com",
        ativo=ativo,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


_AUTH_HEADERS = {"Authorization": "Bearer test-token"}
_CPF_VALIDO = "12345678901"


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
# Fixtures de client
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

def _patch_repo_encontra(leitor: Leitor):
    """Substitui SQLAlchemyLeitorRepository por stub que retorna o leitor."""
    import app.adapters.api.leitores as m
    original = m.SQLAlchemyLeitorRepository

    class _MockRepo:
        def __init__(self, *args, **kwargs): pass
        async def get_by_cpf_hash(self, cpf_hash: str): return leitor

    m.SQLAlchemyLeitorRepository = _MockRepo
    return original


def _patch_repo_nao_encontra():
    """Substitui SQLAlchemyLeitorRepository por stub que retorna None."""
    import app.adapters.api.leitores as m
    original = m.SQLAlchemyLeitorRepository

    class _MockRepo:
        def __init__(self, *args, **kwargs): pass
        async def get_by_cpf_hash(self, cpf_hash: str): return None

    m.SQLAlchemyLeitorRepository = _MockRepo
    return original


def _patch_repo_captura_hash():
    """Stub que captura o hash recebido para assertivas."""
    import app.adapters.api.leitores as m
    original = m.SQLAlchemyLeitorRepository
    received: list[str] = []
    leitor = _make_leitor()

    class _MockRepo:
        def __init__(self, *args, **kwargs): pass
        async def get_by_cpf_hash(self, cpf_hash: str):
            received.append(cpf_hash)
            return leitor

    m.SQLAlchemyLeitorRepository = _MockRepo
    return original, received


def _restore_repo(original):
    import app.adapters.api.leitores as m
    m.SQLAlchemyLeitorRepository = original


# ---------------------------------------------------------------------------
# GET /api/leitores?cpf={cpf}
# ---------------------------------------------------------------------------


class TestBuscarLeitorPorCpf:
    async def test_retorna_200_quando_leitor_existe(self, client: AsyncClient):
        """GET /api/leitores?cpf= retorna 200 com LeitorOut para leitor existente."""
        leitor = _make_leitor()
        orig = _patch_repo_encontra(leitor)
        try:
            response = await client.get(
                f"/api/leitores?cpf={_CPF_VALIDO}",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig)

        assert response.status_code == 200

    async def test_retorna_campos_corretos(self, client: AsyncClient):
        """GET /api/leitores?cpf= retorna id, nome e ativo no body."""
        leitor = _make_leitor("Maria Santos", ativo=True)
        orig = _patch_repo_encontra(leitor)
        try:
            response = await client.get(
                f"/api/leitores?cpf={_CPF_VALIDO}",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig)

        data = response.json()
        assert data["nome"] == "Maria Santos"
        assert data["ativo"] is True
        assert "id" in data

    async def test_retorna_leitor_inativo(self, client: AsyncClient):
        """GET /api/leitores?cpf= retorna 200 com ativo=False para leitor inativo."""
        leitor = _make_leitor("Leitor Inativo", ativo=False)
        orig = _patch_repo_encontra(leitor)
        try:
            response = await client.get(
                f"/api/leitores?cpf={_CPF_VALIDO}",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig)

        assert response.status_code == 200
        assert response.json()["ativo"] is False

    async def test_retorna_404_quando_leitor_nao_encontrado(self, client: AsyncClient):
        """GET /api/leitores?cpf= retorna 404 quando CPF não existe."""
        orig = _patch_repo_nao_encontra()
        try:
            response = await client.get(
                "/api/leitores?cpf=00000000000",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig)

        assert response.status_code == 404

    async def test_retorna_401_sem_token(self, client_sem_auth: AsyncClient):
        """GET /api/leitores?cpf= sem token retorna 401."""
        response = await client_sem_auth.get(f"/api/leitores?cpf={_CPF_VALIDO}")
        assert response.status_code == 401

    async def test_hash_sha256_calculado_corretamente(self, client: AsyncClient):
        """O handler deve calcular SHA-256 do CPF antes de consultar o repositório."""
        orig, received = _patch_repo_captura_hash()
        try:
            await client.get(
                f"/api/leitores?cpf={_CPF_VALIDO}",
                headers=_AUTH_HEADERS,
            )
        finally:
            _restore_repo(orig)

        assert len(received) == 1
        expected_hash = hashlib.sha256(_CPF_VALIDO.encode()).hexdigest()
        assert received[0] == expected_hash

    async def test_retorna_422_sem_parametro_cpf(self, client: AsyncClient):
        """GET /api/leitores sem query param cpf retorna 422."""
        response = await client.get("/api/leitores", headers=_AUTH_HEADERS)
        assert response.status_code == 422
