"""
Testes unitários para as rotas do OPAC (ST-08).

Estratégia: sobrescrever get_db_session (e get_current_user / get_leitor_autenticado
quando a rota é autenticada) e substituir os use cases nos módulos dos routers por
stubs — sem banco de dados.

Cobre:
  - GET /api/obras/publico e GET /api/obras/{id}/publico respondem SEM Authorization,
    sem campos sensíveis, com Cache-Control e validação de page_size.
  - POST /api/leitores (público): 201 pendente, 409 sem dados, 422 CPF inválido.
  - PATCH /api/leitores/{id}/ativar: 200, 404, 401 sem token.
  - GET /api/leitores?cpf= devolve `status`.
  - POST /api/reservas/minhas: usa o leitor resolvido no servidor; 400/409; 401 sem token.
"""
from __future__ import annotations

import base64
import json
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

import app.adapters.api.leitores as leitores_module
import app.adapters.api.obras as obras_module
import app.adapters.api.reservas as reservas_module
from app.adapters.api.deps import get_current_user, get_leitor_autenticado
from app.domain.entities.disponibilidade_obra import DisponibilidadeObra
from app.domain.exceptions import (
    CpfInvalidoError,
    LeitorInativoError,
    LeitorJaCadastradoError,
    LeitorNaoEncontradoError,
    ObraNotFoundError,
    ReservaJaExisteError,
)
from app.infrastructure.database import get_db_session
from app.main import app
from app.use_cases.listar_catalogo_publico import ItemCatalogo, PaginaCatalogo
from app.use_cases.obter_obra_publica import DetalheObraPublica
from tests.domain.repositories.conftest import make_leitor, make_obra, make_reserva

_CAMPOS_SENSIVEIS = ("cpf_hash", "telefone", "email", "leitor_id")
_AUTH = {"Authorization": "Bearer test-token"}


async def _fake_db_session() -> AsyncGenerator:
    yield MagicMock()


@pytest.fixture()
async def client_anonimo() -> AsyncGenerator[AsyncClient, None]:
    """Sem override de autenticação: prova que as rotas públicas não exigem token."""
    app.dependency_overrides[get_db_session] = _fake_db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture()
async def client_operador() -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db_session] = _fake_db_session
    app.dependency_overrides[get_current_user] = lambda: "test-user"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


def _stub_use_case(monkeypatch, module, nome: str, *, retorno=None, erro=None) -> AsyncMock:
    execute = AsyncMock(return_value=retorno, side_effect=erro)
    monkeypatch.setattr(module, nome, MagicMock(return_value=MagicMock(execute=execute)))
    return execute


def _sem_campos_sensiveis(payload: object) -> bool:
    texto = json.dumps(payload)
    return not any(f'"{campo}"' in texto for campo in _CAMPOS_SENSIVEIS)


# ---------------------------------------------------------------------------
# GET /api/obras/publico
# ---------------------------------------------------------------------------


class TestCatalogoPublico:
    async def test_responde_sem_authorization(self, client_anonimo, monkeypatch) -> None:
        obra = make_obra(id=uuid4())
        pagina = PaginaCatalogo([ItemCatalogo(obra, DisponibilidadeObra(obra.id, 1, 0))], 1, 1, 20)
        _stub_use_case(monkeypatch, obras_module, "ListarCatalogoPublicoUseCase", retorno=pagina)

        response = await client_anonimo.get("/api/obras/publico")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["disponivel"] is True
        assert set(body["items"][0]) == {"id", "titulo", "autores", "capa_url", "categoria", "disponivel"}
        assert _sem_campos_sensiveis(body)

    async def test_repassa_termo_e_paginacao(self, client_anonimo, monkeypatch) -> None:
        execute = _stub_use_case(
            monkeypatch, obras_module, "ListarCatalogoPublicoUseCase",
            retorno=PaginaCatalogo([], 0, 2, 10),
        )

        await client_anonimo.get("/api/obras/publico", params={"q": "machado", "page": 2, "page_size": 10})

        execute.assert_awaited_once_with(termo="machado", page=2, page_size=10)

    async def test_define_cache_control(self, client_anonimo, monkeypatch) -> None:
        _stub_use_case(monkeypatch, obras_module, "ListarCatalogoPublicoUseCase", retorno=PaginaCatalogo([], 0, 1, 20))

        response = await client_anonimo.get("/api/obras/publico")

        assert response.headers["cache-control"] == "public, max-age=60"

    async def test_page_size_limitado_a_50(self, client_anonimo) -> None:
        response = await client_anonimo.get("/api/obras/publico", params={"page_size": 51})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/obras/{id}/publico
# ---------------------------------------------------------------------------


class TestObraPublica:
    async def test_responde_sem_authorization(self, client_anonimo, monkeypatch) -> None:
        obra = make_obra(id=uuid4())
        detalhe = DetalheObraPublica(obra, DisponibilidadeObra(obra.id, 0, 2), posicao_ranking=1)
        _stub_use_case(monkeypatch, obras_module, "ObterObraPublicaUseCase", retorno=detalhe)

        response = await client_anonimo.get(f"/api/obras/{obra.id}/publico")

        assert response.status_code == 200
        body = response.json()
        assert body["exemplares_disponiveis"] == 0
        assert body["exemplares_emprestados"] == 2
        assert body["posicao_ranking"] == 1
        assert body["disponivel"] is False
        assert _sem_campos_sensiveis(body)

    async def test_404_quando_obra_nao_encontrada(self, client_anonimo, monkeypatch) -> None:
        _stub_use_case(monkeypatch, obras_module, "ObterObraPublicaUseCase", erro=ObraNotFoundError("x"))

        response = await client_anonimo.get(f"/api/obras/{uuid4()}/publico")

        assert response.status_code == 404

    async def test_422_para_id_que_nao_e_uuid(self, client_anonimo) -> None:
        response = await client_anonimo.get("/api/obras/nao-uuid/publico")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/leitores (pré-cadastro público)
# ---------------------------------------------------------------------------

_PRE_CADASTRO = {"nome": "Ana Lima", "cpf": "529.982.247-25", "telefone": "", "email": "ana@ex.com"}


class TestPreCadastro:
    async def test_201_sem_authorization_e_sem_dados_do_leitor(self, client_anonimo, monkeypatch) -> None:
        execute = _stub_use_case(monkeypatch, leitores_module, "PreCadastrarLeitorUseCase", retorno=make_leitor(ativo=False))

        response = await client_anonimo.post("/api/leitores", json=_PRE_CADASTRO)

        assert response.status_code == 201
        assert response.json() == {"status": "pendente"}
        dados = execute.await_args.args[0]
        assert (dados.cpf, dados.telefone, dados.email) == ("529.982.247-25", None, "ana@ex.com")

    async def test_409_sem_vazar_dados(self, client_anonimo, monkeypatch) -> None:
        _stub_use_case(monkeypatch, leitores_module, "PreCadastrarLeitorUseCase", erro=LeitorJaCadastradoError())

        response = await client_anonimo.post("/api/leitores", json=_PRE_CADASTRO)

        assert response.status_code == 409
        assert response.json() == {
            "detail": "Já existe um cadastro para este CPF. Procure o balcão da biblioteca."
        }

    async def test_422_cpf_invalido(self, client_anonimo, monkeypatch) -> None:
        _stub_use_case(monkeypatch, leitores_module, "PreCadastrarLeitorUseCase", erro=CpfInvalidoError())

        response = await client_anonimo.post("/api/leitores", json={**_PRE_CADASTRO, "cpf": "111.111.111-11"})

        assert response.status_code == 422
        assert response.json()["detail"] == "CPF inválido"

    async def test_422_email_malformado(self, client_anonimo) -> None:
        response = await client_anonimo.post("/api/leitores", json={**_PRE_CADASTRO, "email": "x"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/leitores/{id}/ativar e GET /api/leitores?cpf=
# ---------------------------------------------------------------------------


class TestAtivarLeitor:
    async def test_200_retorna_leitor_ativo(self, client_operador, monkeypatch) -> None:
        leitor = make_leitor(ativo=True)
        _stub_use_case(monkeypatch, leitores_module, "AtivarLeitorUseCase", retorno=leitor)

        response = await client_operador.patch(f"/api/leitores/{leitor.id}/ativar", headers=_AUTH)

        assert response.status_code == 200
        assert response.json()["status"] == "ativo"

    async def test_404_leitor_inexistente(self, client_operador, monkeypatch) -> None:
        _stub_use_case(monkeypatch, leitores_module, "AtivarLeitorUseCase", erro=LeitorNaoEncontradoError("x"))

        response = await client_operador.patch(f"/api/leitores/{uuid4()}/ativar", headers=_AUTH)

        assert response.status_code == 404

    async def test_401_sem_token(self, client_anonimo) -> None:
        response = await client_anonimo.patch(f"/api/leitores/{uuid4()}/ativar")
        assert response.status_code == 401


class TestBuscarLeitorStatus:
    async def test_inclui_status_pendente(self, client_operador, monkeypatch) -> None:
        repo = MagicMock(get_by_cpf_hash=AsyncMock(return_value=make_leitor(ativo=False)))
        monkeypatch.setattr(leitores_module, "SQLAlchemyLeitorRepository", MagicMock(return_value=repo))

        response = await client_operador.get("/api/leitores", params={"cpf": "529.982.247-25"}, headers=_AUTH)

        assert response.json()["status"] == "pendente"


# ---------------------------------------------------------------------------
# POST /api/reservas/minhas
# ---------------------------------------------------------------------------


@pytest.fixture()
async def client_leitor() -> AsyncGenerator[tuple[AsyncClient, object], None]:
    leitor = make_leitor(id=uuid4())
    app.dependency_overrides[get_db_session] = _fake_db_session
    app.dependency_overrides[get_leitor_autenticado] = lambda: leitor
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac, leitor
    app.dependency_overrides.clear()


class TestMinhaReserva:
    async def test_201_usa_leitor_do_token_e_ignora_leitor_id_do_body(self, client_leitor, monkeypatch) -> None:
        client, leitor = client_leitor
        obra_id = uuid4()
        execute = _stub_use_case(
            monkeypatch, reservas_module, "ReservarObraUseCase",
            retorno=(make_reserva(obra_id=obra_id, leitor_id=leitor.id), 2),
        )

        response = await client.post(
            "/api/reservas/minhas", json={"obra_id": str(obra_id), "leitor_id": str(uuid4())}
        )

        assert response.status_code == 201
        assert response.json()["posicao_fila"] == 2
        execute.assert_awaited_once_with(obra_id, leitor.id)

    async def test_400_leitor_pendente(self, client_leitor, monkeypatch) -> None:
        client, _ = client_leitor
        _stub_use_case(monkeypatch, reservas_module, "ReservarObraUseCase", erro=LeitorInativoError("x"))

        response = await client.post("/api/reservas/minhas", json={"obra_id": str(uuid4())})

        assert response.status_code == 400

    async def test_409_reserva_existente(self, client_leitor, monkeypatch) -> None:
        client, _ = client_leitor
        _stub_use_case(monkeypatch, reservas_module, "ReservarObraUseCase", erro=ReservaJaExisteError("o", "l"))

        response = await client.post("/api/reservas/minhas", json={"obra_id": str(uuid4())})

        assert response.status_code == 409

    async def test_401_sem_token(self, client_anonimo) -> None:
        response = await client_anonimo.post("/api/reservas/minhas", json={"obra_id": str(uuid4())})
        assert response.status_code == 401

    async def test_403_token_sem_leitor_vinculado(self, client_anonimo, monkeypatch) -> None:
        repo = MagicMock(get_by_email=AsyncMock(return_value=None))
        monkeypatch.setattr("app.adapters.api.deps.SQLAlchemyLeitorRepository", MagicMock(return_value=repo))
        payload = base64.urlsafe_b64encode(b'{"email":"x@y.com","email_verified":true}').decode().rstrip("=")

        response = await client_anonimo.post(
            "/api/reservas/minhas",
            json={"obra_id": str(uuid4())},
            headers={"Authorization": f"Bearer h.{payload}.s"},
        )

        assert response.status_code == 403
