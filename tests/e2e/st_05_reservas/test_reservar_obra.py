"""
Testes E2E — Sub-Tarefa 2: Reservar Obra (US-015)
Casos: RES-E2E-001 a RES-E2E-014

Cobre:
  - POST /api/reservas cria reserva quando todos os exemplares estão emprestados (201)
  - Campos obrigatórios na resposta: id, obra_id, leitor_id, status, created_at, posicao_fila
  - status inicial = "aguardando"
  - posicao_fila = 1 para o primeiro reservante
  - posicao_fila FIFO por created_at
  - DELETE /api/reservas/{id} muda status para "expirada" (200)
  - DELETE com UUID inexistente retorna 404
  - POST com exemplar disponível retorna 400 com mensagem orientativa
  - Segunda reserva do mesmo leitor retorna 409
  - Leitor inativo retorna 400
  - Endpoints sem token JWT retornam 401
  - Reserva não contém exemplar_id (campo ausente)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.st_05_reservas.conftest import (
    emprestimo_factory,
    exemplar_factory,
    leitor_factory,
    obra_factory,
    reserva_factory,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ─── RES-E2E-001 ──────────────────────────────────────────────────────────────

async def test_res_e2e_001_reservar_com_todos_exemplares_emprestados_retorna_201(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """RES-E2E-001 — POST /api/reservas retorna 201 quando todos os exemplares estão emprestados."""
    obra = await obra_factory(db_session, titulo="Obra RES-001")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)

    response = await client.post(
        "/api/reservas",
        json={"obra_id": str(obra.id), "leitor_id": str(leitor_b.id)},
        headers=auth_headers_operador,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "aguardando"
    assert data["obra_id"] == str(obra.id)
    assert data["leitor_id"] == str(leitor_b.id)


# ─── RES-E2E-002 ──────────────────────────────────────────────────────────────

async def test_res_e2e_002_resposta_contem_campos_obrigatorios(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """RES-E2E-002 — Resposta contém id, obra_id, leitor_id, status, created_at, posicao_fila."""
    obra = await obra_factory(db_session, titulo="Obra RES-002")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)

    response = await client.post(
        "/api/reservas",
        json={"obra_id": str(obra.id), "leitor_id": str(leitor_b.id)},
        headers=auth_headers_operador,
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "obra_id" in data
    assert "leitor_id" in data
    assert "status" in data
    assert "created_at" in data
    assert "posicao_fila" in data


# ─── RES-E2E-003 ──────────────────────────────────────────────────────────────

async def test_res_e2e_003_status_inicial_e_aguardando(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """RES-E2E-003 — Status da reserva criada é 'aguardando'."""
    obra = await obra_factory(db_session, titulo="Obra RES-003")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)

    response = await client.post(
        "/api/reservas",
        json={"obra_id": str(obra.id), "leitor_id": str(leitor_b.id)},
        headers=auth_headers_operador,
    )

    assert response.status_code == 201
    assert response.json()["status"] == "aguardando"


# ─── RES-E2E-004 ──────────────────────────────────────────────────────────────

async def test_res_e2e_004_posicao_fila_e_1_para_primeiro_reservante(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """RES-E2E-004 — posicao_fila é 1 para o primeiro reservante de uma obra."""
    obra = await obra_factory(db_session, titulo="Obra RES-004")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)

    response = await client.post(
        "/api/reservas",
        json={"obra_id": str(obra.id), "leitor_id": str(leitor_b.id)},
        headers=auth_headers_operador,
    )

    assert response.status_code == 201
    assert response.json()["posicao_fila"] == 1


# ─── RES-E2E-005 ──────────────────────────────────────────────────────────────

async def test_res_e2e_005_posicao_fila_fifo_por_created_at(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """RES-E2E-005 — posicao_fila é 2 para o segundo reservante (FIFO por created_at).

    Setup: leitor_b já reservou via factory (visível para HTTP request);
    leitor_c reserva via HTTP e deve retornar posicao_fila=2.
    leitor_b (criado primeiro) tem posição 1 confirmada pela factory direta.
    """
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    obra = await obra_factory(db_session, titulo="Obra RES-005")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session)
    leitor_c = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)

    # leitor_b reserva via factory (created_at menor = primeiro na fila)
    await reserva_factory(
        db_session,
        obra_id=obra.id,
        leitor_id=leitor_b.id,
        created_at=now - timedelta(minutes=5),
    )

    # leitor_c reserva via HTTP (será posição 2)
    resp_c = await client.post(
        "/api/reservas",
        json={"obra_id": str(obra.id), "leitor_id": str(leitor_c.id)},
        headers=auth_headers_operador,
    )

    assert resp_c.status_code == 201
    assert resp_c.json()["posicao_fila"] == 2


# ─── RES-E2E-006 ──────────────────────────────────────────────────────────────

async def test_res_e2e_006_delete_reserva_muda_status_para_expirada(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """RES-E2E-006 — DELETE /api/reservas/{id} retorna 200 e status = 'expirada'.

    Setup: reserva criada via factory (visível para o DELETE HTTP);
    o DELETE cancela a reserva e retorna status='expirada'.
    """
    obra = await obra_factory(db_session, titulo="Obra RES-006")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)

    # Cria reserva via factory (visível para o HTTP DELETE)
    reserva = await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_b.id)

    response = await client.delete(
        f"/api/reservas/{reserva.id}",
        headers=auth_headers_operador,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "expirada"


# ─── RES-E2E-007 ──────────────────────────────────────────────────────────────

async def test_res_e2e_007_delete_reserva_inexistente_retorna_404(
    client: AsyncClient,
    auth_headers_operador: dict,
) -> None:
    """RES-E2E-007 — DELETE /api/reservas/{id} com UUID inexistente retorna 404."""
    import uuid

    response = await client.delete(
        f"/api/reservas/{uuid.uuid4()}",
        headers=auth_headers_operador,
    )

    assert response.status_code == 404


# ─── RES-E2E-008 ──────────────────────────────────────────────────────────────

async def test_res_e2e_008_reservar_com_exemplar_disponivel_retorna_400(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """RES-E2E-008 — POST /api/reservas com exemplar 'disponivel' retorna 400."""
    obra = await obra_factory(db_session, titulo="Obra RES-008")
    await exemplar_factory(db_session, obra_id=obra.id, estado="disponivel")
    leitor = await leitor_factory(db_session)

    response = await client.post(
        "/api/reservas",
        json={"obra_id": str(obra.id), "leitor_id": str(leitor.id)},
        headers=auth_headers_operador,
    )

    assert response.status_code == 400


# ─── RES-E2E-009 ──────────────────────────────────────────────────────────────

async def test_res_e2e_009_mensagem_erro_400_menciona_disponibilidade(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """RES-E2E-009 — Mensagem de erro do 400 menciona disponibilidade."""
    obra = await obra_factory(db_session, titulo="Obra RES-009")
    await exemplar_factory(db_session, obra_id=obra.id, estado="disponivel")
    leitor = await leitor_factory(db_session)

    response = await client.post(
        "/api/reservas",
        json={"obra_id": str(obra.id), "leitor_id": str(leitor.id)},
        headers=auth_headers_operador,
    )

    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "dispon" in detail  # cobre "disponível" e "disponivel"


# ─── RES-E2E-010 ──────────────────────────────────────────────────────────────

async def test_res_e2e_010_segunda_reserva_mesmo_leitor_mesma_obra_retorna_409(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """RES-E2E-010 — Segunda POST /api/reservas do mesmo leitor para a mesma obra retorna 409.

    Setup: primeira reserva criada via factory (visível para o HTTP request);
    a segunda tentativa via HTTP deve retornar 409.
    """
    obra = await obra_factory(db_session, titulo="Obra RES-010")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)

    # Primeira reserva via factory (visível para o segundo HTTP request)
    await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_b.id)

    # Segunda tentativa do mesmo leitor via HTTP deve retornar 409
    resp2 = await client.post(
        "/api/reservas",
        json={"obra_id": str(obra.id), "leitor_id": str(leitor_b.id)},
        headers=auth_headers_operador,
    )

    assert resp2.status_code == 409


# ─── RES-E2E-011 ──────────────────────────────────────────────────────────────

async def test_res_e2e_011_leitor_inativo_retorna_400(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """RES-E2E-011 — POST /api/reservas com leitor inativo retorna 400."""
    obra = await obra_factory(db_session, titulo="Obra RES-011")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_inativo = await leitor_factory(db_session, ativo=False)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)

    response = await client.post(
        "/api/reservas",
        json={"obra_id": str(obra.id), "leitor_id": str(leitor_inativo.id)},
        headers=auth_headers_operador,
    )

    assert response.status_code == 400


# ─── RES-E2E-012 ──────────────────────────────────────────────────────────────

async def test_res_e2e_012_post_reservas_sem_token_retorna_401(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """RES-E2E-012 — POST /api/reservas sem token JWT retorna 401."""
    import uuid

    response = await client.post(
        "/api/reservas",
        json={"obra_id": str(uuid.uuid4()), "leitor_id": str(uuid.uuid4())},
    )

    assert response.status_code == 401


# ─── RES-E2E-013 ──────────────────────────────────────────────────────────────

async def test_res_e2e_013_delete_reserva_sem_token_retorna_401(
    client: AsyncClient,
) -> None:
    """RES-E2E-013 — DELETE /api/reservas/{id} sem token JWT retorna 401."""
    import uuid

    response = await client.delete(f"/api/reservas/{uuid.uuid4()}")

    assert response.status_code == 401


# ─── RES-E2E-014 ──────────────────────────────────────────────────────────────

async def test_res_e2e_014_reserva_nao_contem_exemplar_id(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """RES-E2E-014 — Reserva referencia a obra, não um exemplar (campo exemplar_id ausente)."""
    obra = await obra_factory(db_session, titulo="Obra RES-014")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)

    response = await client.post(
        "/api/reservas",
        json={"obra_id": str(obra.id), "leitor_id": str(leitor_b.id)},
        headers=auth_headers_operador,
    )

    assert response.status_code == 201
    data = response.json()
    assert "exemplar_id" not in data
    assert "obra_id" in data
