"""
Testes E2E — Sub-Tarefa 5: Renovar Empréstimo (US-013)
Casos: REN-E2E-001 a REN-E2E-007

Cobre:
  - POST /api/emprestimos/{id}/renovar retorna 200 com renovacoes=1
  - data_prevista recalculada a partir de hoje
  - Renovação consecutiva incrementa contador de 1 para 2
  - Após 3 renovações, 4ª retorna 422 com mensagem clara
  - Empréstimo inexistente retorna 404
  - Proteção por autenticação (401 sem token)
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


# ─── REN-E2E-001 ─────────────────────────────────────────────────────────────

async def test_ren_e2e_001_renovar_retorna_200_com_renovacoes_1(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """REN-E2E-001 — POST /api/emprestimos/{id}/renovar retorna 200 com renovacoes=1."""
    obra = await obra_factory(db_session, titulo="Obra REN-001")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor = await leitor_factory(db_session)
    emprestimo = await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)

    response = await client.post(
        f"/api/emprestimos/{emprestimo.id}/renovar",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    assert response.json()["renovacoes"] == 1


# ─── REN-E2E-002 ─────────────────────────────────────────────────────────────

async def test_ren_e2e_002_data_prevista_calculada_a_partir_de_hoje(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """REN-E2E-002 — data_prevista na resposta é calculada a partir de hoje (não do prazo anterior)."""
    obra = await obra_factory(db_session, titulo="Obra REN-002")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor = await leitor_factory(db_session)
    # Empréstimo com data_prevista já passada (vencido há 1 dia)
    ontem = datetime.now(timezone.utc) - timedelta(days=1)
    emprestimo = await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=ontem,
    )

    before = datetime.now(tz=timezone.utc)
    response = await client.post(
        f"/api/emprestimos/{emprestimo.id}/renovar",
        headers=auth_headers_operador,
    )
    after = datetime.now(tz=timezone.utc)

    assert response.status_code == 200
    nova_data_str = response.json()["data_prevista"]
    nova_data = datetime.fromisoformat(nova_data_str)
    if nova_data.tzinfo is None:
        nova_data = nova_data.replace(tzinfo=timezone.utc)

    # Nova data_prevista deve ser >= hoje (não a data original no passado)
    assert nova_data >= before, f"data_prevista {nova_data} deve ser >= {before}"

    # E deve ser aproximadamente now + 14 dias
    lower = before + timedelta(days=14) - timedelta(minutes=1)
    upper = after + timedelta(days=14) + timedelta(minutes=1)
    assert lower <= nova_data <= upper, (
        f"data_prevista {nova_data} fora do intervalo [{lower}, {upper}]"
    )


# ─── REN-E2E-003 ─────────────────────────────────────────────────────────────

async def test_ren_e2e_003_renovacao_consecutiva_incrementa_contador(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """REN-E2E-003 — Renovação consecutiva incrementa renovacoes de 1 para 2."""
    obra = await obra_factory(db_session, titulo="Obra REN-003")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor = await leitor_factory(db_session)
    emprestimo = await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)

    # Primeira renovação
    resp1 = await client.post(
        f"/api/emprestimos/{emprestimo.id}/renovar",
        headers=auth_headers_operador,
    )
    assert resp1.status_code == 200
    assert resp1.json()["renovacoes"] == 1

    # Segunda renovação
    resp2 = await client.post(
        f"/api/emprestimos/{emprestimo.id}/renovar",
        headers=auth_headers_operador,
    )
    assert resp2.status_code == 200
    assert resp2.json()["renovacoes"] == 2


# ─── REN-E2E-004 ─────────────────────────────────────────────────────────────

async def test_ren_e2e_004_apos_3_renovacoes_4a_retorna_422(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """REN-E2E-004 — Após 3 renovações, a 4ª retorna 422."""
    obra = await obra_factory(db_session, titulo="Obra REN-004")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor = await leitor_factory(db_session)
    emprestimo = await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)

    # 3 renovações permitidas
    for n in range(1, 4):
        resp = await client.post(
            f"/api/emprestimos/{emprestimo.id}/renovar",
            headers=auth_headers_operador,
        )
        assert resp.status_code == 200, f"Renovação {n} falhou: {resp.text}"
        assert resp.json()["renovacoes"] == n

    # 4ª renovação deve falhar
    response = await client.post(
        f"/api/emprestimos/{emprestimo.id}/renovar",
        headers=auth_headers_operador,
    )
    assert response.status_code == 422


# ─── REN-E2E-005 ─────────────────────────────────────────────────────────────

async def test_ren_e2e_005_mensagem_422_menciona_renovacoes_ou_limite(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """REN-E2E-005 — Mensagem de erro 422 menciona 'renovacoes' ou 'limite'."""
    obra = await obra_factory(db_session, titulo="Obra REN-005")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor = await leitor_factory(db_session)
    emprestimo = await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)

    for _ in range(3):
        await client.post(
            f"/api/emprestimos/{emprestimo.id}/renovar",
            headers=auth_headers_operador,
        )

    response = await client.post(
        f"/api/emprestimos/{emprestimo.id}/renovar",
        headers=auth_headers_operador,
    )
    assert response.status_code == 422
    detail = response.json()["detail"].lower()
    assert "renova" in detail or "limite" in detail, (
        f"Mensagem não menciona renovações/limite: '{detail}'"
    )


# ─── REN-E2E-006 ─────────────────────────────────────────────────────────────

async def test_ren_e2e_006_uuid_inexistente_retorna_404(
    client: AsyncClient,
    auth_headers_operador: dict,
) -> None:
    """REN-E2E-006 — POST /api/emprestimos/{id}/renovar com UUID inexistente retorna 404."""
    response = await client.post(
        f"/api/emprestimos/{uuid.uuid4()}/renovar",
        headers=auth_headers_operador,
    )
    assert response.status_code == 404


# ─── REN-E2E-007 ─────────────────────────────────────────────────────────────

async def test_ren_e2e_007_sem_token_retorna_401(client: AsyncClient) -> None:
    """REN-E2E-007 — POST /api/emprestimos/{id}/renovar sem token JWT retorna 401."""
    response = await client.post(
        f"/api/emprestimos/{uuid.uuid4()}/renovar",
    )
    assert response.status_code == 401
