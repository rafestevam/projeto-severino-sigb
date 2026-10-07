"""
Testes unitários para app/adapters/api/relatorios.py (relatorios_router).

Estratégia: sobrescrever dependências (get_db_session, get_current_user) com
stubs em memória e monkey-patching dos use cases.

Cobre:
  - GET /api/relatorios/dashboard: 200 com campos obrigatórios e sem dados pessoais.
  - GET /api/relatorios/dashboard: 401 sem token.
  - GET /api/relatorios/emprestimos-atrasados: 200 com estrutura correta.
  - GET /api/relatorios/emprestimos-atrasados: 401 sem token.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.api.deps import get_current_user
from app.domain.entities.emprestimo import Emprestimo
from app.infrastructure.database import get_db_session
from app.main import app
from app.use_cases.obter_metricas_dashboard import (
    ExemplaresEstado,
    MetricasDashboard,
    ObraTopEmprestimos,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AUTH_HEADERS = {"Authorization": "Bearer test-token-admin"}

_METRICAS = MetricasDashboard(
    total_obras=5,
    total_exemplares=20,
    total_leitores_ativos=3,
    exemplares_por_estado=ExemplaresEstado(disponivel=15, emprestado=4, baixado=1),
    top_obras_emprestadas=[
        ObraTopEmprestimos(obra_id=uuid4(), titulo="Dom Casmurro", total_emprestimos=8)
    ],
    taxa_perdas=0.05,
    total_doacoes=2,
)


def _make_emprestimo_atrasado() -> Emprestimo:
    return Emprestimo(
        id=uuid4(),
        exemplar_id=uuid4(),
        leitor_id=uuid4(),
        data_checkout=datetime(2025, 1, 1, tzinfo=timezone.utc),
        data_prevista=datetime(2025, 1, 15, tzinfo=timezone.utc),
        data_devolucao=None,
        renovacoes=0,
        status="atrasado",
    )


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
# GET /api/relatorios/dashboard
# ---------------------------------------------------------------------------


class TestDashboardEndpoint:
    async def test_dashboard_retorna_200(self, client: AsyncClient):
        import app.adapters.api.relatorios as m

        orig = m.ObterMetricasDashboardUseCase

        class _Mock:
            def __init__(self, *a, **kw):
                pass

            async def execute(self):
                return _METRICAS

        m.ObterMetricasDashboardUseCase = _Mock
        try:
            resp = await client.get("/api/relatorios/dashboard", headers=_AUTH_HEADERS)
        finally:
            m.ObterMetricasDashboardUseCase = orig

        assert resp.status_code == 200

    async def test_dashboard_contem_campos_obrigatorios(self, client: AsyncClient):
        import app.adapters.api.relatorios as m

        orig = m.ObterMetricasDashboardUseCase

        class _Mock:
            def __init__(self, *a, **kw):
                pass

            async def execute(self):
                return _METRICAS

        m.ObterMetricasDashboardUseCase = _Mock
        try:
            resp = await client.get("/api/relatorios/dashboard", headers=_AUTH_HEADERS)
        finally:
            m.ObterMetricasDashboardUseCase = orig

        data = resp.json()
        assert "total_obras" in data
        assert "total_exemplares" in data
        assert "total_leitores_ativos" in data
        assert "exemplares_por_estado" in data
        assert "top_obras_emprestadas" in data
        assert "taxa_perdas" in data
        assert "total_doacoes" in data

    async def test_dashboard_nao_expoe_dados_pessoais(self, client: AsyncClient):
        import app.adapters.api.relatorios as m

        orig = m.ObterMetricasDashboardUseCase

        class _Mock:
            def __init__(self, *a, **kw):
                pass

            async def execute(self):
                return _METRICAS

        m.ObterMetricasDashboardUseCase = _Mock
        try:
            resp = await client.get("/api/relatorios/dashboard", headers=_AUTH_HEADERS)
        finally:
            m.ObterMetricasDashboardUseCase = orig

        data = resp.json()
        for campo in ("nome", "cpf", "cpf_hash", "telefone", "email"):
            assert campo not in data
            for item in data.get("top_obras_emprestadas", []):
                assert campo not in item

    async def test_dashboard_exemplares_por_estado_tem_tres_chaves(self, client: AsyncClient):
        import app.adapters.api.relatorios as m

        orig = m.ObterMetricasDashboardUseCase

        class _Mock:
            def __init__(self, *a, **kw):
                pass

            async def execute(self):
                return _METRICAS

        m.ObterMetricasDashboardUseCase = _Mock
        try:
            resp = await client.get("/api/relatorios/dashboard", headers=_AUTH_HEADERS)
        finally:
            m.ObterMetricasDashboardUseCase = orig

        estados = resp.json()["exemplares_por_estado"]
        assert "disponivel" in estados
        assert "emprestado" in estados
        assert "baixado" in estados

    async def test_dashboard_sem_token_retorna_401(self, client_sem_auth: AsyncClient):
        resp = await client_sem_auth.get("/api/relatorios/dashboard")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/relatorios/emprestimos-atrasados
# ---------------------------------------------------------------------------


class TestEmprestimosAtrasadosEndpoint:
    async def test_emprestimos_atrasados_retorna_200(self, client: AsyncClient):
        import app.adapters.api.relatorios as m

        emp = _make_emprestimo_atrasado()
        orig = m.ListarEmprestimosAtrasadosUseCase

        class _Mock:
            def __init__(self, *a, **kw):
                pass

            async def execute(self):
                return [emp]

        m.ListarEmprestimosAtrasadosUseCase = _Mock
        try:
            resp = await client.get(
                "/api/relatorios/emprestimos-atrasados", headers=_AUTH_HEADERS
            )
        finally:
            m.ListarEmprestimosAtrasadosUseCase = orig

        assert resp.status_code == 200

    async def test_emprestimos_atrasados_estrutura_correta(self, client: AsyncClient):
        import app.adapters.api.relatorios as m

        emp = _make_emprestimo_atrasado()
        orig = m.ListarEmprestimosAtrasadosUseCase

        class _Mock:
            def __init__(self, *a, **kw):
                pass

            async def execute(self):
                return [emp]

        m.ListarEmprestimosAtrasadosUseCase = _Mock
        try:
            resp = await client.get(
                "/api/relatorios/emprestimos-atrasados", headers=_AUTH_HEADERS
            )
        finally:
            m.ListarEmprestimosAtrasadosUseCase = orig

        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 1

    async def test_emprestimos_atrasados_nao_expoe_dados_pessoais(self, client: AsyncClient):
        import app.adapters.api.relatorios as m

        emp = _make_emprestimo_atrasado()
        orig = m.ListarEmprestimosAtrasadosUseCase

        class _Mock:
            def __init__(self, *a, **kw):
                pass

            async def execute(self):
                return [emp]

        m.ListarEmprestimosAtrasadosUseCase = _Mock
        try:
            resp = await client.get(
                "/api/relatorios/emprestimos-atrasados", headers=_AUTH_HEADERS
            )
        finally:
            m.ListarEmprestimosAtrasadosUseCase = orig

        for item in resp.json().get("items", []):
            assert "nome" not in item
            assert "cpf" not in item
            assert "telefone" not in item

    async def test_emprestimos_atrasados_sem_token_retorna_401(
        self, client_sem_auth: AsyncClient
    ):
        resp = await client_sem_auth.get("/api/relatorios/emprestimos-atrasados")
        assert resp.status_code == 401

    async def test_emprestimos_atrasados_lista_vazia_retorna_200(
        self, client: AsyncClient
    ):
        import app.adapters.api.relatorios as m

        orig = m.ListarEmprestimosAtrasadosUseCase

        class _Mock:
            def __init__(self, *a, **kw):
                pass

            async def execute(self):
                return []

        m.ListarEmprestimosAtrasadosUseCase = _Mock
        try:
            resp = await client.get(
                "/api/relatorios/emprestimos-atrasados", headers=_AUTH_HEADERS
            )
        finally:
            m.ListarEmprestimosAtrasadosUseCase = orig

        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
