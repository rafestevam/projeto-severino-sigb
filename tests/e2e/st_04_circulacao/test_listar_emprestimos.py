"""
Testes E2E — Sub-Tarefa 7: Listar Empréstimos com Filtros (US-036)
Casos: LST-E2E-001 a LST-E2E-012

Cobre:
  - GET /api/emprestimos retorna 200 com estrutura {items, total, page, page_size}
  - page_size padrão = 20
  - Paginação funciona com page e page_size
  - Filtro por status retorna apenas empréstimos com aquele status
  - Filtro por leitor_id retorna apenas empréstimos daquele leitor
  - Cada item contém titulo_obra não nulo
  - Resposta não expõe dados pessoais (nome, cpf, telefone)
  - Combinação de filtros funciona
  - Proteção por autenticação (401 sem token)
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.st_04_circulacao.conftest import (
    emprestimo_factory,
    exemplar_factory,
    leitor_factory,
    obra_factory,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ─── LST-E2E-001 ─────────────────────────────────────────────────────────────

async def test_lst_e2e_001_get_emprestimos_retorna_200_com_estrutura_correta(
    client: AsyncClient, auth_headers_operador: dict
) -> None:
    """LST-E2E-001 — GET /api/emprestimos retorna 200 com estrutura {items, total, page, page_size}."""
    response = await client.get("/api/emprestimos", headers=auth_headers_operador)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


# ─── LST-E2E-002 ─────────────────────────────────────────────────────────────

async def test_lst_e2e_002_page_size_padrao_e_20(
    client: AsyncClient, auth_headers_operador: dict
) -> None:
    """LST-E2E-002 — page_size padrão é 20 quando não informado."""
    response = await client.get("/api/emprestimos", headers=auth_headers_operador)
    assert response.status_code == 200
    assert response.json()["page_size"] == 20


# ─── LST-E2E-003 ─────────────────────────────────────────────────────────────

async def test_lst_e2e_003_paginacao_limita_itens_por_pagina(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LST-E2E-003 — GET /api/emprestimos?page=1&page_size=2 retorna no máximo 2 itens."""
    # Cria 5 empréstimos
    for i in range(5):
        obra = await obra_factory(db_session, titulo=f"Obra LST-003-{i}")
        exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
        leitor = await leitor_factory(db_session)
        await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)

    response = await client.get(
        "/api/emprestimos?page=1&page_size=2",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 2
    assert data["page_size"] == 2
    assert data["page"] == 1


# ─── LST-E2E-004 ─────────────────────────────────────────────────────────────

async def test_lst_e2e_004_total_reflete_numero_real_de_emprestimos(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LST-E2E-004 — Campo total reflete o número real de empréstimos no banco."""
    # Consulta antes de inserir para ter baseline
    resp_antes = await client.get("/api/emprestimos", headers=auth_headers_operador)
    total_antes = resp_antes.json()["total"]

    # Cria 3 novos
    for i in range(3):
        obra = await obra_factory(db_session, titulo=f"Obra LST-004-{i}")
        exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
        leitor = await leitor_factory(db_session)
        await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)

    resp_depois = await client.get("/api/emprestimos", headers=auth_headers_operador)
    total_depois = resp_depois.json()["total"]
    assert total_depois == total_antes + 3


# ─── LST-E2E-005 ─────────────────────────────────────────────────────────────

async def test_lst_e2e_005_filtro_status_ativo(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LST-E2E-005 — GET /api/emprestimos?status=ativo retorna apenas empréstimos ativos."""
    obra = await obra_factory(db_session, titulo="Obra LST-005")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id, status="ativo")

    response = await client.get(
        "/api/emprestimos?status=ativo", headers=auth_headers_operador
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    assert all(item["status"] == "ativo" for item in items)


# ─── LST-E2E-006 ─────────────────────────────────────────────────────────────

async def test_lst_e2e_006_filtro_status_devolvido(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LST-E2E-006 — GET /api/emprestimos?status=devolvido retorna apenas empréstimos devolvidos."""
    obra = await obra_factory(db_session, titulo="Obra LST-006")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session)
    await emprestimo_factory(
        db_session, exemplar_id=exemplar.id, leitor_id=leitor.id, status="devolvido"
    )

    response = await client.get(
        "/api/emprestimos?status=devolvido", headers=auth_headers_operador
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    assert all(item["status"] == "devolvido" for item in items)


# ─── LST-E2E-007 ─────────────────────────────────────────────────────────────

async def test_lst_e2e_007_filtro_por_leitor_id(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LST-E2E-007 — GET /api/emprestimos?leitor_id={id} retorna apenas empréstimos daquele leitor."""
    leitor_a = await leitor_factory(db_session, nome="Leitor A LST-007")
    leitor_b = await leitor_factory(db_session, nome="Leitor B LST-007")

    # 2 empréstimos para leitor A
    for i in range(2):
        obra = await obra_factory(db_session, titulo=f"Obra LST-007-A-{i}")
        exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
        await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)

    # 1 empréstimo para leitor B
    obra_b = await obra_factory(db_session, titulo="Obra LST-007-B")
    exemplar_b = await exemplar_factory(db_session, obra_id=obra_b.id, estado="emprestado")
    await emprestimo_factory(db_session, exemplar_id=exemplar_b.id, leitor_id=leitor_b.id)

    response = await client.get(
        f"/api/emprestimos?leitor_id={leitor_a.id}",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    assert all(item["leitor_id"] == str(leitor_a.id) for item in items)


# ─── LST-E2E-008 ─────────────────────────────────────────────────────────────

async def test_lst_e2e_008_cada_item_contem_titulo_obra(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LST-E2E-008 — Cada item da resposta contém titulo_obra não nulo."""
    obra = await obra_factory(db_session, titulo="Dom Casmurro")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor = await leitor_factory(db_session)
    emp = await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)

    response = await client.get(
        f"/api/emprestimos?leitor_id={leitor.id}",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1

    item = next(i for i in items if i["leitor_id"] == str(leitor.id))
    assert item.get("titulo_obra") is not None
    assert item["titulo_obra"] == "Dom Casmurro"


# ─── LST-E2E-009 ─────────────────────────────────────────────────────────────

async def test_lst_e2e_009_resposta_nao_expoe_dados_pessoais(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LST-E2E-009 — Resposta não contém nome, cpf ou telefone em nenhum item."""
    obra = await obra_factory(db_session, titulo="Obra LST-009")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)

    response = await client.get("/api/emprestimos", headers=auth_headers_operador)
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert "nome" not in item, f"Campo 'nome' exposto no item: {item}"
        assert "cpf" not in item, f"Campo 'cpf' exposto no item: {item}"
        assert "telefone" not in item, f"Campo 'telefone' exposto no item: {item}"
        assert "email" not in item, f"Campo 'email' exposto no item: {item}"


# ─── LST-E2E-010 ─────────────────────────────────────────────────────────────

async def test_lst_e2e_010_sem_filtros_retorna_emprestimos_de_diferentes_leitores(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LST-E2E-010 — GET /api/emprestimos sem filtros retorna empréstimos de leitores diferentes."""
    leitor_x = await leitor_factory(db_session, nome="Leitor X LST-010")
    leitor_y = await leitor_factory(db_session, nome="Leitor Y LST-010")

    obra_x = await obra_factory(db_session, titulo="Obra LST-010-X")
    exemplar_x = await exemplar_factory(db_session, obra_id=obra_x.id, estado="emprestado")
    await emprestimo_factory(db_session, exemplar_id=exemplar_x.id, leitor_id=leitor_x.id)

    obra_y = await obra_factory(db_session, titulo="Obra LST-010-Y")
    exemplar_y = await exemplar_factory(db_session, obra_id=obra_y.id, estado="emprestado")
    await emprestimo_factory(db_session, exemplar_id=exemplar_y.id, leitor_id=leitor_y.id)

    response = await client.get("/api/emprestimos", headers=auth_headers_operador)
    assert response.status_code == 200
    items = response.json()["items"]
    leitor_ids_na_resposta = {item["leitor_id"] for item in items}
    assert str(leitor_x.id) in leitor_ids_na_resposta
    assert str(leitor_y.id) in leitor_ids_na_resposta


# ─── LST-E2E-011 ─────────────────────────────────────────────────────────────

async def test_lst_e2e_011_sem_token_retorna_401(client: AsyncClient) -> None:
    """LST-E2E-011 — GET /api/emprestimos sem token JWT retorna 401."""
    response = await client.get("/api/emprestimos")
    assert response.status_code == 401


# ─── LST-E2E-012 ─────────────────────────────────────────────────────────────

async def test_lst_e2e_012_combinacao_filtros_status_e_leitor_id(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LST-E2E-012 — Combinação de filtros status=ativo&leitor_id={id} funciona corretamente."""
    leitor = await leitor_factory(db_session, nome="Leitor LST-012")

    # 1 empréstimo ativo deste leitor
    obra_a = await obra_factory(db_session, titulo="Obra LST-012-A")
    exemplar_a = await exemplar_factory(db_session, obra_id=obra_a.id, estado="emprestado")
    await emprestimo_factory(
        db_session, exemplar_id=exemplar_a.id, leitor_id=leitor.id, status="ativo"
    )

    # 1 empréstimo devolvido deste leitor (não deve aparecer no filtro ativo)
    obra_b = await obra_factory(db_session, titulo="Obra LST-012-B")
    exemplar_b = await exemplar_factory(db_session, obra_id=obra_b.id)
    await emprestimo_factory(
        db_session, exemplar_id=exemplar_b.id, leitor_id=leitor.id, status="devolvido"
    )

    response = await client.get(
        f"/api/emprestimos?status=ativo&leitor_id={leitor.id}",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "ativo"
    assert items[0]["leitor_id"] == str(leitor.id)
