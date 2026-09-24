"""
Testes E2E — Sub-Tarefa 3: Realizar Check-Out (US-011)
Casos: CHK-E2E-001 a CHK-E2E-013

Cobre:
  - POST /api/emprestimos cria empréstimo (201) com campos corretos
  - data_prevista calculada como data_checkout + 14 dias
  - Estado do exemplar atualizado para "emprestado"
  - Violações: exemplar já emprestado (409), leitor inexistente (404),
    exemplar inexistente (404), limite de empréstimos atingido (422)
  - Proteção por autenticação (401 sem token)

Estratégia: leitores e obras/exemplares são criados via factory (db_session) para
independência de routers ainda não implementados (ex: /api/leitores).
Obras usadas no payload da API são criadas via POST /api/obras quando possível.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

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


# ─── CHK-E2E-001 ─────────────────────────────────────────────────────────────

async def test_chk_e2e_001_checkout_retorna_201(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CHK-E2E-001 — POST /api/emprestimos com exemplar disponível e leitor ativo retorna 201."""
    obra = await obra_factory(db_session, titulo="Obra CHK-001")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="disponivel")
    leitor = await leitor_factory(db_session)

    response = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor.id)},
        headers=auth_headers_operador,
    )
    assert response.status_code == 201


# ─── CHK-E2E-002 ─────────────────────────────────────────────────────────────

async def test_chk_e2e_002_resposta_contem_campos_obrigatorios(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CHK-E2E-002 — Resposta contém id, exemplar_id, leitor_id, status, data_prevista, renovacoes=0."""
    obra = await obra_factory(db_session, titulo="Obra CHK-002")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session)

    response = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor.id)},
        headers=auth_headers_operador,
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["exemplar_id"] == str(exemplar.id)
    assert data["leitor_id"] == str(leitor.id)
    assert "status" in data
    assert "data_prevista" in data
    assert data["renovacoes"] == 0


# ─── CHK-E2E-003 ─────────────────────────────────────────────────────────────

async def test_chk_e2e_003_status_ativo_no_checkout(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CHK-E2E-003 — Status do empréstimo criado é 'ativo'."""
    obra = await obra_factory(db_session, titulo="Obra CHK-003")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session)

    response = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor.id)},
        headers=auth_headers_operador,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "ativo"


# ─── CHK-E2E-004 ─────────────────────────────────────────────────────────────

async def test_chk_e2e_004_data_prevista_calculada_com_prazo_padrao(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CHK-E2E-004 — data_prevista é aproximadamente data_checkout + 14 dias."""
    obra = await obra_factory(db_session, titulo="Obra CHK-004")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session)

    before = datetime.now(tz=timezone.utc)
    response = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor.id)},
        headers=auth_headers_operador,
    )
    after = datetime.now(tz=timezone.utc)

    assert response.status_code == 201
    data_prevista_str = response.json()["data_prevista"]
    data_prevista = datetime.fromisoformat(data_prevista_str)
    if data_prevista.tzinfo is None:
        data_prevista = data_prevista.replace(tzinfo=timezone.utc)

    lower = before + timedelta(days=14) - timedelta(minutes=1)
    upper = after + timedelta(days=14) + timedelta(minutes=1)
    assert lower <= data_prevista <= upper, (
        f"data_prevista {data_prevista} fora do intervalo [{lower}, {upper}]"
    )


# ─── CHK-E2E-005 ─────────────────────────────────────────────────────────────

async def test_chk_e2e_005_exemplar_fica_emprestado_apos_checkout(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CHK-E2E-005 — Estado do exemplar é 'emprestado' após o check-out."""
    obra = await obra_factory(db_session, titulo="Obra CHK-005")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session)

    await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor.id)},
        headers=auth_headers_operador,
    )

    resp_exemplar = await client.get(
        f"/api/exemplares/{exemplar.id}", headers=auth_headers_operador
    )
    assert resp_exemplar.status_code == 200
    assert resp_exemplar.json()["estado"] == "emprestado"


# ─── CHK-E2E-006 ─────────────────────────────────────────────────────────────

async def test_chk_e2e_006_exemplar_ja_emprestado_retorna_409(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CHK-E2E-006 — POST /api/emprestimos para exemplar com estado 'emprestado' retorna 409."""
    obra = await obra_factory(db_session, titulo="Obra CHK-006")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor_a = await leitor_factory(db_session, nome="Leitor A CHK-006")
    leitor_b = await leitor_factory(db_session, nome="Leitor B CHK-006")

    # Primeiro checkout — deve passar
    resp1 = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor_a.id)},
        headers=auth_headers_operador,
    )
    assert resp1.status_code == 201

    # Segundo checkout do mesmo exemplar — deve retornar 409
    response = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor_b.id)},
        headers=auth_headers_operador,
    )
    assert response.status_code == 409


# ─── CHK-E2E-007 ─────────────────────────────────────────────────────────────

async def test_chk_e2e_007_mensagem_409_menciona_disponibilidade(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CHK-E2E-007 — Mensagem de erro 409 menciona disponibilidade do exemplar."""
    obra = await obra_factory(db_session, titulo="Obra CHK-007")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor_a = await leitor_factory(db_session, nome="Leitor A CHK-007")
    leitor_b = await leitor_factory(db_session, nome="Leitor B CHK-007")

    await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor_a.id)},
        headers=auth_headers_operador,
    )
    response = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor_b.id)},
        headers=auth_headers_operador,
    )
    assert response.status_code == 409
    detail = response.json()["detail"].lower()
    assert "dispon" in detail or "emprest" in detail, (
        f"Mensagem não menciona disponibilidade: '{detail}'"
    )


# ─── CHK-E2E-008 ─────────────────────────────────────────────────────────────

async def test_chk_e2e_008_leitor_inexistente_retorna_404(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CHK-E2E-008 — POST /api/emprestimos com leitor inexistente retorna 404."""
    obra = await obra_factory(db_session, titulo="Obra CHK-008")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)

    response = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(uuid.uuid4())},
        headers=auth_headers_operador,
    )
    assert response.status_code == 404


# ─── CHK-E2E-009 ─────────────────────────────────────────────────────────────

async def test_chk_e2e_009_exemplar_inexistente_retorna_404(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CHK-E2E-009 — POST /api/emprestimos com exemplar inexistente retorna 404."""
    leitor = await leitor_factory(db_session)

    response = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(uuid.uuid4()), "leitor_id": str(leitor.id)},
        headers=auth_headers_operador,
    )
    assert response.status_code == 404


# ─── CHK-E2E-010 ─────────────────────────────────────────────────────────────

async def test_chk_e2e_010_leitor_com_limite_atingido_retorna_422(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CHK-E2E-010 — Leitor com 3 empréstimos ativos recebe 422 ao tentar novo check-out."""
    leitor = await leitor_factory(db_session, nome="Leitor Limite CHK-010")

    # Criar 3 obras/exemplares e emprestar todas ao mesmo leitor
    for i in range(3):
        obra = await obra_factory(db_session, titulo=f"Obra Limite CHK-010-{i}")
        exemplar = await exemplar_factory(db_session, obra_id=obra.id)
        resp = await client.post(
            "/api/emprestimos",
            json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor.id)},
            headers=auth_headers_operador,
        )
        assert resp.status_code == 201, f"Empréstimo {i+1} falhou: {resp.text}"

    # 4ª tentativa deve falhar
    obra_extra = await obra_factory(db_session, titulo="Obra Extra CHK-010")
    exemplar_extra = await exemplar_factory(db_session, obra_id=obra_extra.id)
    response = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar_extra.id), "leitor_id": str(leitor.id)},
        headers=auth_headers_operador,
    )
    assert response.status_code == 422


# ─── CHK-E2E-011 ─────────────────────────────────────────────────────────────

async def test_chk_e2e_011_mensagem_422_menciona_limite(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CHK-E2E-011 — Mensagem de erro 422 menciona limite de empréstimos."""
    leitor = await leitor_factory(db_session, nome="Leitor Msg CHK-011")

    for i in range(3):
        obra = await obra_factory(db_session, titulo=f"Obra Msg CHK-011-{i}")
        exemplar = await exemplar_factory(db_session, obra_id=obra.id)
        await client.post(
            "/api/emprestimos",
            json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor.id)},
            headers=auth_headers_operador,
        )

    obra_extra = await obra_factory(db_session, titulo="Obra Msg Extra CHK-011")
    exemplar_extra = await exemplar_factory(db_session, obra_id=obra_extra.id)
    response = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar_extra.id), "leitor_id": str(leitor.id)},
        headers=auth_headers_operador,
    )
    assert response.status_code == 422
    detail = response.json()["detail"].lower()
    assert "limite" in detail, f"Mensagem não menciona limite: '{detail}'"


# ─── CHK-E2E-012 ─────────────────────────────────────────────────────────────

async def test_chk_e2e_012_sem_token_retorna_401(client: AsyncClient) -> None:
    """CHK-E2E-012 — POST /api/emprestimos sem token JWT retorna 401."""
    response = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(uuid.uuid4()), "leitor_id": str(uuid.uuid4())},
    )
    assert response.status_code == 401


# ─── CHK-E2E-013 ─────────────────────────────────────────────────────────────

async def test_chk_e2e_013_exemplar_tem_obra_id_correto(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CHK-E2E-013 — Exemplar disponível tem campo obra_id acessível e correto."""
    obra = await obra_factory(db_session, titulo="Obra CHK-013")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="disponivel")

    resp_exemplar = await client.get(
        f"/api/exemplares/{exemplar.id}", headers=auth_headers_operador
    )
    assert resp_exemplar.status_code == 200
    assert resp_exemplar.json()["obra_id"] == str(obra.id)
