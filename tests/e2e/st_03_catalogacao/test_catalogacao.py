"""
Testes de integração — ST-03 Catalogação
Cobre: US-009 (cadastrar obra), US-010 (criar exemplares)
US-008 (buscar metadados por ISBN) é testado separadamente pois depende de gateway externo.

Cada teste recebe `client` (httpx.AsyncClient apontando para a FastAPI via ASGI) e
`auth_headers_operador` / `auth_headers_admin` do conftest compartilhado.

Status dos testes:
  - Testes marcados com `@pytest.mark.integration` são executados via:
      pytest -m integration tests/e2e/
  - Testes marcados com `@pytest.mark.xfail(reason="ST-03 não implementada")` falharão
    corretamente até que os endpoints sejam implementados — sem quebrar o CI atual.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# ─── Payloads reutilizáveis ───────────────────────────────────────────────────

OBRA_VALIDA = {
    "isbn": "9788535902778",
    "titulo": "Dom Casmurro",
    "autores": ["Machado de Assis"],
    "editora": "Ática",
    "ano": 1899,
    "categoria": "Literatura Brasileira",
    "capa_url": None,
}

OBRA_SEM_ISBN = {
    "isbn": None,
    "titulo": "Obra Sem ISBN",
    "autores": ["Autor Desconhecido"],
    "editora": "Editora Independente",
    "ano": 2024,
    "categoria": "Ficção",
    "capa_url": None,
}


# ─── US-009: Cadastrar obra ───────────────────────────────────────────────────


@pytest.mark.xfail(reason="ST-03 não implementada ainda", strict=False)
async def test_cadastrar_obra_retorna_201_e_id(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-009 — POST /api/obras cria uma nova obra e retorna status 201 com o id gerado.
    """
    response = await client.post("/api/obras", json=OBRA_VALIDA, headers=auth_headers_operador)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["titulo"] == OBRA_VALIDA["titulo"]
    assert data["isbn"] == OBRA_VALIDA["isbn"]


@pytest.mark.xfail(reason="ST-03 não implementada ainda", strict=False)
async def test_cadastrar_obra_sem_isbn_retorna_201(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-009 — ISBN é opcional; obra sem ISBN deve ser aceita normalmente.
    """
    response = await client.post("/api/obras", json=OBRA_SEM_ISBN, headers=auth_headers_operador)
    assert response.status_code == 201
    data = response.json()
    assert data["isbn"] is None
    assert data["titulo"] == OBRA_SEM_ISBN["titulo"]


@pytest.mark.xfail(reason="ST-03 não implementada ainda", strict=False)
async def test_cadastrar_obra_duplicada_retorna_409(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-009 — Duplicidade de ISBN é detectada e retorna erro 409 (Conflict).
    O sistema não cria obra com ISBN já existente.
    """
    await client.post("/api/obras", json=OBRA_VALIDA, headers=auth_headers_operador)
    response = await client.post("/api/obras", json=OBRA_VALIDA, headers=auth_headers_operador)
    assert response.status_code == 409
    assert "isbn" in response.json()["detail"].lower()


@pytest.mark.xfail(reason="ST-03 não implementada ainda", strict=False)
async def test_cadastrar_obra_sem_autenticacao_retorna_401(client: AsyncClient):
    """
    US-009 — Endpoint exige autenticação; sem token deve retornar 401.
    """
    response = await client.post("/api/obras", json=OBRA_VALIDA)
    assert response.status_code == 401


@pytest.mark.xfail(reason="ST-03 não implementada ainda", strict=False)
async def test_listar_obras_retorna_200_com_paginacao(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-009 — GET /api/obras lista obras com paginação padrão de 20 itens.
    """
    await client.post("/api/obras", json=OBRA_VALIDA, headers=auth_headers_operador)
    response = await client.get("/api/obras", headers=auth_headers_operador)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert data["page_size"] == 20


@pytest.mark.xfail(reason="ST-03 não implementada ainda", strict=False)
async def test_listar_obras_filtra_por_titulo(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-009 — GET /api/obras?titulo=Dom filtra obras pelo título (busca parcial).
    """
    await client.post("/api/obras", json=OBRA_VALIDA, headers=auth_headers_operador)
    response = await client.get("/api/obras?titulo=Dom", headers=auth_headers_operador)
    assert response.status_code == 200
    items = response.json()["items"]
    assert any("Dom" in obra["titulo"] for obra in items)


@pytest.mark.xfail(reason="ST-03 não implementada ainda", strict=False)
async def test_listar_obras_filtra_por_categoria(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-009 — GET /api/obras?categoria=Literatura filtra obras pela categoria.
    """
    await client.post("/api/obras", json=OBRA_VALIDA, headers=auth_headers_operador)
    response = await client.get(
        "/api/obras?categoria=Literatura Brasileira", headers=auth_headers_operador
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(obra["categoria"] == "Literatura Brasileira" for obra in items)


@pytest.mark.xfail(reason="ST-03 não implementada ainda", strict=False)
async def test_isbn_invalido_retorna_422(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-009 — ISBN com dígito verificador inválido deve ser rejeitado com 422.
    """
    obra_isbn_invalido = {**OBRA_VALIDA, "isbn": "9999999999999"}  # ISBN inválido
    response = await client.post("/api/obras", json=obra_isbn_invalido, headers=auth_headers_operador)
    assert response.status_code == 422


# ─── US-010: Criar exemplares ─────────────────────────────────────────────────


@pytest.mark.xfail(reason="ST-03 não implementada ainda", strict=False)
async def test_criar_exemplares_retorna_201_com_codigos_qr(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-010 — POST /api/obras/{obra_id}/exemplares cria N exemplares com códigos QR
    únicos no formato LIB-{ANO}-{SEQUENCIAL:05d}.
    """
    # Arrange: criar obra
    obra_resp = await client.post("/api/obras", json=OBRA_VALIDA, headers=auth_headers_operador)
    obra_id = obra_resp.json()["id"]

    # Act
    response = await client.post(
        f"/api/obras/{obra_id}/exemplares",
        json={"quantidade": 3, "localizacao_estante": "A-01"},
        headers=auth_headers_operador,
    )

    # Assert
    assert response.status_code == 201
    exemplares = response.json()
    assert len(exemplares) == 3
    codigos = [e["codigo_qr"] for e in exemplares]
    # Todos os códigos devem ser únicos
    assert len(set(codigos)) == 3
    # Formato LIB-{ANO}-{SEQUENCIAL:05d}
    import re
    for codigo in codigos:
        assert re.match(r"LIB-\d{4}-\d{5}", codigo), f"Formato inválido: {codigo}"


@pytest.mark.xfail(reason="ST-03 não implementada ainda", strict=False)
async def test_exemplares_criados_ficam_disponiveis(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-010 — Exemplares recém-criados devem ter estado 'disponivel'.
    """
    obra_resp = await client.post("/api/obras", json=OBRA_VALIDA, headers=auth_headers_operador)
    obra_id = obra_resp.json()["id"]

    response = await client.post(
        f"/api/obras/{obra_id}/exemplares",
        json={"quantidade": 1, "localizacao_estante": "B-02"},
        headers=auth_headers_operador,
    )
    exemplar = response.json()[0]
    assert exemplar["estado"] == "disponivel"


@pytest.mark.xfail(reason="ST-03 não implementada ainda", strict=False)
async def test_criar_exemplar_obra_inexistente_retorna_404(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-010 — Tentar criar exemplares para obra que não existe retorna 404.
    """
    response = await client.post(
        "/api/obras/00000000-0000-0000-0000-000000000099/exemplares",
        json={"quantidade": 1, "localizacao_estante": "X-01"},
        headers=auth_headers_operador,
    )
    assert response.status_code == 404


@pytest.mark.xfail(reason="ST-03 não implementada ainda", strict=False)
async def test_etiqueta_pdf_retorna_content_type_pdf(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-010 — GET /api/exemplares/{codigo_qr}/etiqueta.pdf retorna PDF binário.
    """
    # Arrange: criar obra e exemplar
    obra_resp = await client.post("/api/obras", json=OBRA_VALIDA, headers=auth_headers_operador)
    obra_id = obra_resp.json()["id"]
    exemplares_resp = await client.post(
        f"/api/obras/{obra_id}/exemplares",
        json={"quantidade": 1, "localizacao_estante": "C-01"},
        headers=auth_headers_operador,
    )
    codigo_qr = exemplares_resp.json()[0]["codigo_qr"]

    # Act
    response = await client.get(
        f"/api/exemplares/{codigo_qr}/etiqueta.pdf",
        headers=auth_headers_operador,
    )

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


# ─── US-008: Buscar metadados por ISBN (gateway externo) ─────────────────────


@pytest.mark.xfail(reason="ST-03 não implementada ainda", strict=False)
async def test_buscar_metadados_isbn_retorna_200_com_dados(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-008 — POST /api/obras/isbn/{isbn} retorna metadados do Open Library/Google Books.
    Teste depende de conectividade externa — pode ser marcado como skip em CI sem rede.
    """
    response = await client.post(
        "/api/obras/isbn/9788535902778",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    data = response.json()
    # Os campos podem vir parcialmente preenchidos dependendo da fonte
    assert "titulo" in data


@pytest.mark.xfail(reason="ST-03 não implementada ainda", strict=False)
async def test_buscar_metadados_isbn_inexistente_retorna_schema_vazio(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-008 — ISBN não encontrado em nenhuma fonte retorna schema vazio para
    preenchimento manual (não retorna 404).
    """
    response = await client.post(
        "/api/obras/isbn/0000000000000",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    data = response.json()
    # Schema vazio: campos presentes mas nulos
    assert data.get("titulo") is None or data.get("titulo") == ""
