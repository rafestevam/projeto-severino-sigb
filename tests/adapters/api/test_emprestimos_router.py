"""
Testes unitários para app/adapters/api/emprestimos.py (emprestimos_router).

Estratégia: montar a FastAPI app, sobrescrever dependências
(get_db_session, get_current_user) com stubs em memória que não tocam
banco de dados nem rede. Os use cases são mockados para isolamento total.

Cobre:
  - POST /api/emprestimos: 201 sucesso, 404 exemplar não encontrado, 409 exemplar não disponível, 400 leitor inativo, 422 limite atingido, 401 sem token.
  - POST /api/emprestimos/devolver-por-qr: 200 sucesso, 404 sem ativo por QR, 401 sem token.
  - POST /api/emprestimos/{id}/devolver: 200 sucesso, 404 empréstimo não encontrado, 404 exemplar não encontrado, 401 sem token.
  - POST /api/emprestimos/{id}/renovar: 200 sucesso, 404 empréstimo não encontrado, 422 limite renovações, 401 sem token.
  - GET /api/emprestimos: 200 paginação e filtros, 401 sem token.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.api.deps import get_current_user
from app.domain.entities.emprestimo import Emprestimo, EmprestimoComTitulo
from app.domain.exceptions import (
    EmprestimoNaoEncontradoError,
    EmprestimoSemAtivoPorQrError,
    ExemplarNaoDisponivelError,
    ExemplarNotFoundError,
    LeitorInativoError,
    LimiteEmprestimosAtingidoError,
    LimiteRenovacoesAtingidoError,
)
from app.infrastructure.database import get_db_session
from app.main import app

# ---------------------------------------------------------------------------
# Helpers — fábricas de entidades
# ---------------------------------------------------------------------------

_EMPRESTIMO_ID = uuid4()
_EXEMPLAR_ID = uuid4()
_LEITOR_ID = uuid4()


def _make_emprestimo(
    emprestimo_id: UUID = _EMPRESTIMO_ID,
    exemplar_id: UUID = _EXEMPLAR_ID,
    leitor_id: UUID = _LEITOR_ID,
    status: str = "ativo",
    renovacoes: int = 0,
    data_devolucao: datetime | None = None,
) -> Emprestimo:
    return Emprestimo(
        id=emprestimo_id,
        exemplar_id=exemplar_id,
        leitor_id=leitor_id,
        data_checkout=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        data_prevista=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        data_devolucao=data_devolucao,
        renovacoes=renovacoes,
        status=status,
    )


def _make_emprestimo_com_titulo(
    emprestimo_id: UUID = _EMPRESTIMO_ID,
    titulo_obra: str = "Dom Casmurro",
) -> EmprestimoComTitulo:
    return EmprestimoComTitulo(
        id=emprestimo_id,
        exemplar_id=_EXEMPLAR_ID,
        leitor_id=_LEITOR_ID,
        data_checkout=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        data_prevista=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        data_devolucao=None,
        renovacoes=0,
        status="ativo",
        titulo_obra=titulo_obra,
    )


_AUTH_HEADERS = {"Authorization": "Bearer test-token"}


# ---------------------------------------------------------------------------
# Fixtures — overrides de dependência
# ---------------------------------------------------------------------------

async def _fake_db_session() -> AsyncGenerator:
    mock_session = AsyncMock()
    yield mock_session


def _override_auth():
    app.dependency_overrides[get_current_user] = lambda: "test-user"


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
# POST /api/emprestimos (Check-out)
# ---------------------------------------------------------------------------


class TestCheckoutEndpoint:
    async def test_checkout_sucesso_retorna_201(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        emp = _make_emprestimo()
        orig = m.RealizarCheckoutUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, exemplar_id, leitor_id): return emp

        m.RealizarCheckoutUseCase = _Mock
        try:
            resp = await client.post(
                "/api/emprestimos",
                json={"exemplar_id": str(_EXEMPLAR_ID), "leitor_id": str(_LEITOR_ID)},
                headers=_AUTH_HEADERS,
            )
        finally:
            m.RealizarCheckoutUseCase = orig

        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == str(_EMPRESTIMO_ID)
        assert data["status"] == "ativo"

    async def test_checkout_exemplar_not_found_retorna_404(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        orig = m.RealizarCheckoutUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, exemplar_id, leitor_id):
                raise ExemplarNotFoundError(str(exemplar_id))

        m.RealizarCheckoutUseCase = _Mock
        try:
            resp = await client.post(
                "/api/emprestimos",
                json={"exemplar_id": str(_EXEMPLAR_ID), "leitor_id": str(_LEITOR_ID)},
                headers=_AUTH_HEADERS,
            )
        finally:
            m.RealizarCheckoutUseCase = orig

        assert resp.status_code == 404

    async def test_checkout_exemplar_nao_disponivel_retorna_409(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        orig = m.RealizarCheckoutUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, exemplar_id, leitor_id):
                raise ExemplarNaoDisponivelError(str(exemplar_id), "emprestado")

        m.RealizarCheckoutUseCase = _Mock
        try:
            resp = await client.post(
                "/api/emprestimos",
                json={"exemplar_id": str(_EXEMPLAR_ID), "leitor_id": str(_LEITOR_ID)},
                headers=_AUTH_HEADERS,
            )
        finally:
            m.RealizarCheckoutUseCase = orig

        assert resp.status_code == 409

    async def test_checkout_leitor_inativo_retorna_400(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        orig = m.RealizarCheckoutUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, exemplar_id, leitor_id):
                raise LeitorInativoError(str(leitor_id))

        m.RealizarCheckoutUseCase = _Mock
        try:
            resp = await client.post(
                "/api/emprestimos",
                json={"exemplar_id": str(_EXEMPLAR_ID), "leitor_id": str(_LEITOR_ID)},
                headers=_AUTH_HEADERS,
            )
        finally:
            m.RealizarCheckoutUseCase = orig

        assert resp.status_code == 400

    async def test_checkout_limite_emprestimos_atingido_retorna_422(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        orig = m.RealizarCheckoutUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, exemplar_id, leitor_id):
                raise LimiteEmprestimosAtingidoError(str(leitor_id), 3)

        m.RealizarCheckoutUseCase = _Mock
        try:
            resp = await client.post(
                "/api/emprestimos",
                json={"exemplar_id": str(_EXEMPLAR_ID), "leitor_id": str(_LEITOR_ID)},
                headers=_AUTH_HEADERS,
            )
        finally:
            m.RealizarCheckoutUseCase = orig

        assert resp.status_code == 422

    async def test_checkout_sem_auth_retorna_401(self, client_sem_auth: AsyncClient):
        resp = await client_sem_auth.post(
            "/api/emprestimos",
            json={"exemplar_id": str(_EXEMPLAR_ID), "leitor_id": str(_LEITOR_ID)},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/emprestimos/devolver-por-qr (Devolução por QR)
# ---------------------------------------------------------------------------


class TestDevolverPorQrEndpoint:
    async def test_devolver_por_qr_sucesso_retorna_200(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        emp = _make_emprestimo(
            status="devolvido",
            data_devolucao=datetime(2025, 1, 10, 10, 0, tzinfo=timezone.utc),
        )
        orig = m.ProcessarDevolucaoUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, codigo_qr): return emp

        m.ProcessarDevolucaoUseCase = _Mock
        try:
            resp = await client.post(
                "/api/emprestimos/devolver-por-qr",
                json={"codigo_qr": "LIB-2025-00001"},
                headers=_AUTH_HEADERS,
            )
        finally:
            m.ProcessarDevolucaoUseCase = orig

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "devolvido"

    async def test_devolver_por_qr_sem_ativo_retorna_404(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        orig = m.ProcessarDevolucaoUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, codigo_qr):
                raise EmprestimoSemAtivoPorQrError(codigo_qr)

        m.ProcessarDevolucaoUseCase = _Mock
        try:
            resp = await client.post(
                "/api/emprestimos/devolver-por-qr",
                json={"codigo_qr": "LIB-2025-00001"},
                headers=_AUTH_HEADERS,
            )
        finally:
            m.ProcessarDevolucaoUseCase = orig

        assert resp.status_code == 404

    async def test_devolver_por_qr_sem_auth_retorna_401(self, client_sem_auth: AsyncClient):
        resp = await client_sem_auth.post(
            "/api/emprestimos/devolver-por-qr",
            json={"codigo_qr": "LIB-2025-00001"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/emprestimos/{id}/devolver (Devolução por ID)
# ---------------------------------------------------------------------------


class TestDevolverPorIdEndpoint:
    async def test_devolver_por_id_sucesso_retorna_200(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        emp = _make_emprestimo()
        emp_devolvido = _make_emprestimo(
            status="devolvido",
            data_devolucao=datetime(2025, 1, 10, 10, 0, tzinfo=timezone.utc),
        )

        orig_emp_repo = m.SQLAlchemyEmprestimoRepository
        orig_ex_repo = m.SQLAlchemyExemplarRepository
        orig_uc = m.ProcessarDevolucaoUseCase

        class _MockEmpRepo:
            def __init__(self, session): pass
            async def get_by_id(self, id): return emp

        class _MockExemplar:
            codigo_qr = "LIB-2025-00001"

        class _MockExRepo:
            def __init__(self, session): pass
            async def get_by_id(self, id): return _MockExemplar()

        class _MockUc:
            def __init__(self, *a, **kw): pass
            async def execute(self, codigo_qr): return emp_devolvido

        m.SQLAlchemyEmprestimoRepository = _MockEmpRepo
        m.SQLAlchemyExemplarRepository = _MockExRepo
        m.ProcessarDevolucaoUseCase = _MockUc
        try:
            resp = await client.post(
                f"/api/emprestimos/{_EMPRESTIMO_ID}/devolver",
                headers=_AUTH_HEADERS,
            )
        finally:
            m.SQLAlchemyEmprestimoRepository = orig_emp_repo
            m.SQLAlchemyExemplarRepository = orig_ex_repo
            m.ProcessarDevolucaoUseCase = orig_uc

        assert resp.status_code == 200
        assert resp.json()["status"] == "devolvido"

    async def test_devolver_por_id_emprestimo_inexistente_retorna_404(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        orig_emp_repo = m.SQLAlchemyEmprestimoRepository

        class _MockEmpRepo:
            def __init__(self, session): pass
            async def get_by_id(self, id): return None

        m.SQLAlchemyEmprestimoRepository = _MockEmpRepo
        try:
            resp = await client.post(
                f"/api/emprestimos/{_EMPRESTIMO_ID}/devolver",
                headers=_AUTH_HEADERS,
            )
        finally:
            m.SQLAlchemyEmprestimoRepository = orig_emp_repo

        assert resp.status_code == 404

    async def test_devolver_por_id_exemplar_inexistente_retorna_404(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        emp = _make_emprestimo()
        orig_emp_repo = m.SQLAlchemyEmprestimoRepository
        orig_ex_repo = m.SQLAlchemyExemplarRepository

        class _MockEmpRepo:
            def __init__(self, session): pass
            async def get_by_id(self, id): return emp

        class _MockExRepo:
            def __init__(self, session): pass
            async def get_by_id(self, id): return None

        m.SQLAlchemyEmprestimoRepository = _MockEmpRepo
        m.SQLAlchemyExemplarRepository = _MockExRepo
        try:
            resp = await client.post(
                f"/api/emprestimos/{_EMPRESTIMO_ID}/devolver",
                headers=_AUTH_HEADERS,
            )
        finally:
            m.SQLAlchemyEmprestimoRepository = orig_emp_repo
            m.SQLAlchemyExemplarRepository = orig_ex_repo

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/emprestimos/{id}/renovar (Renovação)
# ---------------------------------------------------------------------------


class TestRenovarEmprestimoEndpoint:
    async def test_renovar_sucesso_retorna_200(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        emp = _make_emprestimo(renovacoes=1)
        orig = m.RenovarEmprestimoUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, emprestimo_id): return emp

        m.RenovarEmprestimoUseCase = _Mock
        try:
            resp = await client.post(
                f"/api/emprestimos/{_EMPRESTIMO_ID}/renovar",
                headers=_AUTH_HEADERS,
            )
        finally:
            m.RenovarEmprestimoUseCase = orig

        assert resp.status_code == 200
        data = resp.json()
        assert data["renovacoes"] == 1

    async def test_renovar_inexistente_retorna_404(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        orig = m.RenovarEmprestimoUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, emprestimo_id):
                raise EmprestimoNaoEncontradoError(str(emprestimo_id))

        m.RenovarEmprestimoUseCase = _Mock
        try:
            resp = await client.post(
                f"/api/emprestimos/{_EMPRESTIMO_ID}/renovar",
                headers=_AUTH_HEADERS,
            )
        finally:
            m.RenovarEmprestimoUseCase = orig

        assert resp.status_code == 404

    async def test_renovar_limite_atingido_retorna_422(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        orig = m.RenovarEmprestimoUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, emprestimo_id):
                raise LimiteRenovacoesAtingidoError(str(emprestimo_id), 3)

        m.RenovarEmprestimoUseCase = _Mock
        try:
            resp = await client.post(
                f"/api/emprestimos/{_EMPRESTIMO_ID}/renovar",
                headers=_AUTH_HEADERS,
            )
        finally:
            m.RenovarEmprestimoUseCase = orig

        assert resp.status_code == 422

    async def test_renovar_sem_auth_retorna_401(self, client_sem_auth: AsyncClient):
        resp = await client_sem_auth.post(f"/api/emprestimos/{_EMPRESTIMO_ID}/renovar")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/emprestimos (Listar)
# ---------------------------------------------------------------------------


class TestListarEmprestimosEndpoint:
    async def test_listar_retorna_200_com_paginacao(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        items = [_make_emprestimo_com_titulo()]
        orig = m.ListarEmprestimosUseCase

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, **kwargs): return items, 1

        m.ListarEmprestimosUseCase = _Mock
        try:
            resp = await client.get("/api/emprestimos", headers=_AUTH_HEADERS)
        finally:
            m.ListarEmprestimosUseCase = orig

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["titulo_obra"] == "Dom Casmurro"
        assert data["page"] == 1
        assert data["page_size"] == 20

    async def test_listar_filtros_repassados(self, client: AsyncClient):
        import app.adapters.api.emprestimos as m
        orig = m.ListarEmprestimosUseCase
        captured_kwargs = {}

        class _Mock:
            def __init__(self, *a, **kw): pass
            async def execute(self, **kwargs):
                captured_kwargs.update(kwargs)
                return [], 0

        m.ListarEmprestimosUseCase = _Mock
        try:
            resp = await client.get(
                f"/api/emprestimos?leitor_id={_LEITOR_ID}&status=ativo&page=2&page_size=10",
                headers=_AUTH_HEADERS,
            )
        finally:
            m.ListarEmprestimosUseCase = orig

        assert resp.status_code == 200
        assert captured_kwargs["leitor_id"] == _LEITOR_ID
        assert captured_kwargs["status"] == "ativo"
        assert captured_kwargs["page"] == 2
        assert captured_kwargs["page_size"] == 10

    async def test_listar_sem_auth_retorna_401(self, client_sem_auth: AsyncClient):
        resp = await client_sem_auth.get("/api/emprestimos")
        assert resp.status_code == 401
