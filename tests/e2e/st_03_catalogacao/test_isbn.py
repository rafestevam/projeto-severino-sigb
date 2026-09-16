"""
Testes e2e — US-008: Buscar Metadados por ISBN
Sub-Tarefa 2 do plano ST-03.

Cobre os casos ISBN-001 a ISBN-008.

Todos os testes usam FakeIsbnGateway via override de dependência FastAPI —
nenhuma chamada HTTP real é feita às APIs externas (Open Library, Google Books, CBL).

Marcados com xfail até que os endpoints de catalogação sejam implementados.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# ISBN que o FakeIsbnGateway resolve com metadados completos
ISBN_HIT = "9788535902778"

# ISBN que o FakeIsbnGateway retorna schema vazio (nenhuma fonte encontrou)
ISBN_EMPTY = "0000000000000"


# ─── ISBN-001: metadados encontrados retornam status 200 ─────────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras/isbn/{isbn} não implementado", strict=False)
async def test_isbn_001_metadados_encontrados_retornam_200(
    client: AsyncClient,
    auth_headers_operador: dict,
    isbn_gateway_override,
):
    """
    ISBN-001 — ISBN encontrado na primeira fonte retorna metadados completos com status 200.
    US-008: "retorna metadados do livro quando encontrado em alguma fonte"
    """
    response = await client.post(
        f"/api/obras/isbn/{ISBN_HIT}",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("titulo") is not None
    assert data["titulo"] != ""


# ─── ISBN-002: resposta contém campos esperados ───────────────────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras/isbn/{isbn} não implementado", strict=False)
async def test_isbn_002_resposta_contem_campos_bibliograficos(
    client: AsyncClient,
    auth_headers_operador: dict,
    isbn_gateway_override,
):
    """
    ISBN-002 — Resposta contém campos: titulo, autores, editora, capa_url.
    US-008: schema de retorno com metadados bibliográficos.
    """
    response = await client.post(
        f"/api/obras/isbn/{ISBN_HIT}",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    data = response.json()
    assert "titulo" in data
    assert "autores" in data
    assert "editora" in data
    assert "capa_url" in data
    # Campos com valores para ISBN com hit
    assert isinstance(data["autores"], list)
    assert len(data["autores"]) >= 1


# ─── ISBN-003: nenhuma fonte retorna dados → schema vazio, sem erro ───────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras/isbn/{isbn} não implementado", strict=False)
async def test_isbn_003_fallback_schema_vazio(
    client: AsyncClient,
    auth_headers_operador: dict,
    isbn_gateway_override,
):
    """
    ISBN-003 — Quando nenhuma fonte retorna dados, status é 200 com schema de campos vazios/nulos.
    US-008: "endpoint retorna um schema vazio (sem erro) para preenchimento manual"
    """
    response = await client.post(
        f"/api/obras/isbn/{ISBN_EMPTY}",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    data = response.json()
    # Deve ser um objeto (não um erro HTTP)
    assert isinstance(data, dict)
    # Campos presentes mas nulos ou vazios
    titulo = data.get("titulo")
    assert titulo is None or titulo == ""


# ─── ISBN-004: ausência de chave CBL não causa erro ──────────────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras/isbn/{isbn} não implementado", strict=False)
async def test_isbn_004_cbl_ignorada_sem_chave(
    client: AsyncClient,
    auth_headers_operador: dict,
    isbn_gateway_override,
    monkeypatch,
):
    """
    ISBN-004 — ISBN sem chave CBL configurada não causa erro.
    US-008: "a ausência de chave da CBL não causa erro"

    Remove a env var da chave CBL para simular ambiente sem configuração de CBL.
    O FakeIsbnGateway garante que Open Library e Google Books também não retornam dados,
    mas o endpoint deve responder 200 (e não 500).
    """
    monkeypatch.delenv("CBL_API_KEY", raising=False)

    response = await client.post(
        f"/api/obras/isbn/{ISBN_HIT}",
        headers=auth_headers_operador,
    )
    # Sem chave CBL, o endpoint não deve explodir — retorna 200 normalmente
    assert response.status_code == 200


# ─── ISBN-005: sem token JWT → 401 ────────────────────────────────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras/isbn/{isbn} não implementado", strict=False)
async def test_isbn_005_sem_token_retorna_401(client: AsyncClient):
    """
    ISBN-005 — Requisição sem token JWT retorna 401.
    US-008: "endpoint exige autenticação"
    """
    response = await client.post(f"/api/obras/isbn/{ISBN_HIT}")
    assert response.status_code == 401


# ─── ISBN-006: token de role não autorizada → 403 ────────────────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras/isbn/{isbn} não implementado", strict=False)
async def test_isbn_006_role_nao_autorizada_retorna_403(
    client: AsyncClient,
    auth_headers_leitor: dict,
):
    """
    ISBN-006 — Requisição com token de role não autorizada retorna 403.
    US-008: "role `admin` ou `operador`"
    """
    response = await client.post(
        f"/api/obras/isbn/{ISBN_HIT}",
        headers=auth_headers_leitor,
    )
    assert response.status_code == 403


# ─── ISBN-007: token de operador válido → 200 ────────────────────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras/isbn/{isbn} não implementado", strict=False)
async def test_isbn_007_token_operador_retorna_200(
    client: AsyncClient,
    auth_headers_operador: dict,
    isbn_gateway_override,
):
    """
    ISBN-007 — Requisição com token de `operador` válido retorna 200.
    US-008: "role `admin` ou `operador`"
    """
    response = await client.post(
        f"/api/obras/isbn/{ISBN_HIT}",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200


# ─── ISBN-008: token de admin válido → 200 ───────────────────────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras/isbn/{isbn} não implementado", strict=False)
async def test_isbn_008_token_admin_retorna_200(
    client: AsyncClient,
    auth_headers_admin: dict,
    isbn_gateway_override,
):
    """
    ISBN-008 — Requisição com token de `admin` válido retorna 200.
    US-008: "role `admin` ou `operador`"
    """
    response = await client.post(
        f"/api/obras/isbn/{ISBN_HIT}",
        headers=auth_headers_admin,
    )
    assert response.status_code == 200
