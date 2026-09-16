"""
Testes e2e — US-009: Cadastrar Obra com ou sem ISBN
Sub-Tarefa 3 do plano ST-03.

Cobre os casos OBR-E2E-001 a OBR-E2E-017.

Estratégia:
  - Cada teste opera dentro do SAVEPOINT revertido pelo conftest pai (isolamento total).
  - As factories do conftest local são usadas quando é necessário pré-popular o banco
    sem passar pela API (ex: para testes de filtro com múltiplas obras).
  - Testes de listagem/filtro criam obras diretamente via factory para maior controle.

Marcados com xfail até que os endpoints de catalogação sejam implementados.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.st_03_catalogacao.conftest import obra_factory

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# ─── Payloads reutilizáveis ───────────────────────────────────────────────────

OBRA_COMPLETA = {
    "isbn": "9788535902778",
    "titulo": "Dom Casmurro",
    "autores": ["Machado de Assis"],
    "editora": "Ática",
    "ano": 1899,
    "categoria": "Literatura Brasileira",
    "capa_url": "https://example.com/dom-casmurro.jpg",
}

OBRA_SEM_ISBN_OMITIDO = {
    "titulo": "Obra Sem ISBN (campo omitido)",
    "autores": ["Autor Anônimo"],
    "editora": "Editora Independente",
    "ano": 2024,
    "categoria": "Ficção",
}

OBRA_SEM_ISBN_NULL = {
    "isbn": None,
    "titulo": "Obra Sem ISBN (isbn null)",
    "autores": ["Autor Anônimo"],
    "editora": "Editora Independente",
    "ano": 2024,
    "categoria": "Ficção",
}

# ISBN-10 válido (check digit = 0)
ISBN_10_VALIDO = "0306406152"

# ISBN-13 válido alternativo
ISBN_13_VALIDO = "9780306406157"

# ISBN com check digit inválido (modificado na última posição)
ISBN_INVALIDO = "9999999999999"


# ─── OBR-E2E-001: POST /api/obras com todos os campos retorna 201 e id ────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras não implementado", strict=False)
async def test_obr_e2e_001_post_obra_retorna_201_e_id(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """
    OBR-E2E-001 — POST /api/obras com todos os campos retorna 201 e body com `id`.
    US-009: "POST /api/obras cria uma nova obra com todos os campos bibliográficos"
    """
    response = await client.post("/api/obras", json=OBRA_COMPLETA, headers=auth_headers_operador)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["titulo"] == OBRA_COMPLETA["titulo"]
    assert data["isbn"] == OBRA_COMPLETA["isbn"]


# ─── OBR-E2E-002: obra criada via POST aparece em GET /api/obras ──────────────

@pytest.mark.xfail(reason="Endpoints POST/GET /api/obras não implementados", strict=False)
async def test_obr_e2e_002_obra_criada_aparece_na_listagem(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """
    OBR-E2E-002 — Obra criada via POST aparece em GET /api/obras.
    US-009: obra aparece no catálogo.
    """
    await client.post("/api/obras", json=OBRA_COMPLETA, headers=auth_headers_operador)

    response = await client.get("/api/obras", headers=auth_headers_operador)
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(o["isbn"] == OBRA_COMPLETA["isbn"] for o in items)


# ─── OBR-E2E-003: POST sem ISBN (campo omitido) retorna 201 ─────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras não implementado", strict=False)
async def test_obr_e2e_003_post_obra_sem_isbn_omitido_retorna_201(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """
    OBR-E2E-003 — POST /api/obras sem ISBN (isbn omitido) retorna 201.
    US-009: "O ISBN é opcional"
    """
    response = await client.post(
        "/api/obras", json=OBRA_SEM_ISBN_OMITIDO, headers=auth_headers_operador
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["isbn"] is None


# ─── OBR-E2E-004: POST sem ISBN com isbn=null retorna 201 ────────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras não implementado", strict=False)
async def test_obr_e2e_004_post_obra_isbn_null_retorna_201(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """
    OBR-E2E-004 — POST /api/obras com isbn: null retorna 201.
    US-009: "obras sem ISBN podem ser cadastradas normalmente"
    """
    response = await client.post(
        "/api/obras", json=OBRA_SEM_ISBN_NULL, headers=auth_headers_operador
    )
    assert response.status_code == 201
    data = response.json()
    assert data["isbn"] is None


# ─── OBR-E2E-005: GET /api/obras retorna lista paginada com page_size padrão ──

@pytest.mark.xfail(reason="Endpoint GET /api/obras não implementado", strict=False)
async def test_obr_e2e_005_get_obras_paginacao_padrao(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    OBR-E2E-005 — GET /api/obras sem filtros retorna lista com paginação padrão (20 por página).
    US-009: "GET /api/obras lista obras com paginação"
    """
    # Garante pelo menos uma obra no banco
    await obra_factory(db_session, titulo="Obra Paginação Teste")

    response = await client.get("/api/obras", headers=auth_headers_operador)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert data["page_size"] == 20
    assert data["page"] == 1


# ─── OBR-E2E-006: GET /api/obras?page=1&page_size=2 retorna até 2 obras ──────

@pytest.mark.xfail(reason="Endpoint GET /api/obras não implementado", strict=False)
async def test_obr_e2e_006_paginacao_com_parametros(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    OBR-E2E-006 — GET /api/obras?page=1&page_size=2 retorna até 2 obras com total correto.
    US-009: "paginação com parâmetros page e page_size"
    """
    # Persiste 5 obras diretamente para controle preciso do total
    for i in range(5):
        await obra_factory(db_session, titulo=f"Obra Paginação {i + 1}")

    response = await client.get(
        "/api/obras?page=1&page_size=2", headers=auth_headers_operador
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 2
    assert data["total"] >= 5
    assert data["page"] == 1


# ─── OBR-E2E-007: GET /api/obras?titulo=Python filtra por título (case-insensitive)

@pytest.mark.xfail(reason="Endpoint GET /api/obras não implementado", strict=False)
async def test_obr_e2e_007_filtro_por_titulo_case_insensitive(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    OBR-E2E-007 — GET /api/obras?titulo=Python retorna apenas obras cujo título contém "Python".
    US-009: "suporta filtro por título" (case-insensitive).
    """
    await obra_factory(db_session, titulo="Algoritmos em Python")
    await obra_factory(db_session, titulo="Python Fluente")
    await obra_factory(db_session, titulo="Clean Code")

    response = await client.get(
        "/api/obras?titulo=python",  # minúsculo — deve ser case-insensitive
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    # Apenas obras com "Python" no título (case-insensitive)
    assert len(items) >= 2
    for obra in items:
        assert "python" in obra["titulo"].lower(), (
            f"Obra inesperada no filtro: {obra['titulo']}"
        )


# ─── OBR-E2E-008: GET /api/obras?autor=Knuth filtra por autor ────────────────

@pytest.mark.xfail(reason="Endpoint GET /api/obras não implementado", strict=False)
async def test_obr_e2e_008_filtro_por_autor(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    OBR-E2E-008 — GET /api/obras?autor=Knuth retorna apenas obras de autores que contêm "Knuth".
    US-009: "suporta filtro por autor"
    """
    await obra_factory(db_session, titulo="The Art of Computer Programming", autores=["Donald Knuth"])
    await obra_factory(db_session, titulo="Clean Code", autores=["Robert C. Martin"])

    response = await client.get("/api/obras?autor=Knuth", headers=auth_headers_operador)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    for obra in items:
        autores_str = " ".join(obra["autores"]).lower()
        assert "knuth" in autores_str, (
            f"Obra com autor inesperado no filtro: {obra['autores']}"
        )


# ─── OBR-E2E-009: GET /api/obras?categoria=Ciência filtra por categoria ────────

@pytest.mark.xfail(reason="Endpoint GET /api/obras não implementado", strict=False)
async def test_obr_e2e_009_filtro_por_categoria(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    OBR-E2E-009 — GET /api/obras?categoria=Ciência retorna apenas obras da categoria informada.
    US-009: "suporta filtro por categoria"
    """
    await obra_factory(db_session, titulo="Física Quântica", categoria="Ciência")
    await obra_factory(db_session, titulo="Dom Casmurro", categoria="Literatura Brasileira")

    response = await client.get(
        "/api/obras?categoria=Ciência", headers=auth_headers_operador
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    for obra in items:
        assert "ciência" in obra["categoria"].lower(), (
            f"Obra com categoria inesperada no filtro: {obra['categoria']}"
        )


# ─── OBR-E2E-010: POST com ISBN duplicado retorna 4xx ─────────────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras não implementado", strict=False)
async def test_obr_e2e_010_isbn_duplicado_retorna_4xx(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """
    OBR-E2E-010 — POST /api/obras com ISBN já cadastrado retorna 4xx com mensagem de erro.
    US-009: "Duplicidade de ISBN é detectada e retorna erro informativo"
    """
    await client.post("/api/obras", json=OBRA_COMPLETA, headers=auth_headers_operador)
    response = await client.post("/api/obras", json=OBRA_COMPLETA, headers=auth_headers_operador)

    assert 400 <= response.status_code < 500
    detail = response.json().get("detail", "")
    assert "isbn" in detail.lower() or "duplica" in detail.lower()


# ─── OBR-E2E-011: ISBN duplicado não cria obra duplicada ──────────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras não implementado", strict=False)
async def test_obr_e2e_011_isbn_duplicado_nao_cria_obra_duplicada(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """
    OBR-E2E-011 — Segunda tentativa de POST com mesmo ISBN não cria obra duplicada.
    US-009: "não cria obra duplicada"
    """
    await client.post("/api/obras", json=OBRA_COMPLETA, headers=auth_headers_operador)
    await client.post("/api/obras", json=OBRA_COMPLETA, headers=auth_headers_operador)  # ignorado

    response = await client.get(
        f"/api/obras?titulo={OBRA_COMPLETA['titulo']}", headers=auth_headers_operador
    )
    assert response.status_code == 200
    obras_com_isbn = [
        o for o in response.json()["items"] if o["isbn"] == OBRA_COMPLETA["isbn"]
    ]
    assert len(obras_com_isbn) == 1


# ─── OBR-E2E-012: POST sem token JWT retorna 401 ─────────────────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras não implementado", strict=False)
async def test_obr_e2e_012_post_sem_token_retorna_401(client: AsyncClient):
    """
    OBR-E2E-012 — POST /api/obras sem token JWT retorna 401.
    US-009: "endpoint exige autenticação"
    """
    response = await client.post("/api/obras", json=OBRA_COMPLETA)
    assert response.status_code == 401


# ─── OBR-E2E-013: POST com role não autorizada retorna 403 ───────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras não implementado", strict=False)
async def test_obr_e2e_013_post_role_nao_autorizada_retorna_403(
    client: AsyncClient,
    auth_headers_leitor: dict,
):
    """
    OBR-E2E-013 — POST /api/obras com token de role não autorizada retorna 403.
    US-009: "role `admin` ou `operador`"
    """
    response = await client.post("/api/obras", json=OBRA_COMPLETA, headers=auth_headers_leitor)
    assert response.status_code == 403


# ─── OBR-E2E-014: GET /api/obras sem token retorna 401 ───────────────────────

@pytest.mark.xfail(reason="Endpoint GET /api/obras não implementado", strict=False)
async def test_obr_e2e_014_get_sem_token_retorna_401(client: AsyncClient):
    """
    OBR-E2E-014 — GET /api/obras sem token retorna 401.
    US-009: endpoint protegido.
    """
    response = await client.get("/api/obras")
    assert response.status_code == 401


# ─── OBR-E2E-015: ISBN-10 válido é aceito ────────────────────────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras não implementado", strict=False)
async def test_obr_e2e_015_isbn10_valido_aceito(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """
    OBR-E2E-015 — ISBN-10 válido é aceito no POST /api/obras.
    US-009: "Validar ISBN-10 e ISBN-13 com check digit"
    """
    obra_isbn10 = {
        "isbn": ISBN_10_VALIDO,
        "titulo": "Obra ISBN-10",
        "autores": ["Autor Teste"],
        "editora": "Editora Teste",
        "ano": 2000,
        "categoria": "Técnico",
    }
    response = await client.post("/api/obras", json=obra_isbn10, headers=auth_headers_operador)
    assert response.status_code == 201


# ─── OBR-E2E-016: ISBN-13 válido é aceito ────────────────────────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras não implementado", strict=False)
async def test_obr_e2e_016_isbn13_valido_aceito(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """
    OBR-E2E-016 — ISBN-13 válido é aceito no POST /api/obras.
    US-009: "Validar ISBN-13 com check digit"
    """
    obra_isbn13 = {
        "isbn": ISBN_13_VALIDO,
        "titulo": "Obra ISBN-13",
        "autores": ["Autor Teste"],
        "editora": "Editora Teste",
        "ano": 2005,
        "categoria": "Técnico",
    }
    response = await client.post("/api/obras", json=obra_isbn13, headers=auth_headers_operador)
    assert response.status_code == 201


# ─── OBR-E2E-017: ISBN com check digit inválido retorna 422 ──────────────────

@pytest.mark.xfail(reason="Endpoint POST /api/obras não implementado", strict=False)
async def test_obr_e2e_017_isbn_invalido_retorna_422(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """
    OBR-E2E-017 — ISBN com check digit inválido retorna 422 (validação Pydantic).
    US-009: "Validar ISBN com check digit antes de persistir"
    """
    obra_isbn_invalido = {
        "isbn": ISBN_INVALIDO,
        "titulo": "Obra ISBN Inválido",
        "autores": ["Autor Teste"],
        "editora": "Editora Teste",
        "ano": 2024,
        "categoria": "Técnico",
    }
    response = await client.post(
        "/api/obras", json=obra_isbn_invalido, headers=auth_headers_operador
    )
    assert response.status_code == 422
