"""
Testes E2E — Sub-Tarefa 4: Realizar Check-In por QR Code (US-012)
Casos: CIN-E2E-001 a CIN-E2E-010

Cobre:
  - POST /api/emprestimos/devolver-por-qr resolve empréstimo ativo pelo codigo_qr (200)
  - status="devolvido" e data_devolucao preenchida
  - Exemplar volta a estado "disponivel"
  - Bip sem empréstimo ativo retorna 404
  - Reserva "aguardando" é ativada para "disponivel" após devolução
  - Fluxo alternativo POST /api/emprestimos/{id}/devolver
  - Proteção por autenticação (401 sem token)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.reserva import ReservaModel
from tests.e2e.st_04_circulacao.conftest import (
    emprestimo_factory,
    exemplar_factory,
    leitor_factory,
    obra_factory,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ─── Helpers via API ──────────────────────────────────────────────────────────

async def _checkout(client: AsyncClient, exemplar_id: str, leitor_id: str, headers: dict) -> dict:
    resp = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": exemplar_id, "leitor_id": leitor_id},
        headers=headers,
    )
    assert resp.status_code == 201, f"Checkout falhou: {resp.text}"
    return resp.json()


# ─── CIN-E2E-001 ─────────────────────────────────────────────────────────────

async def test_cin_e2e_001_devolver_por_qr_retorna_200(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CIN-E2E-001 — POST /api/emprestimos/devolver-por-qr com QR de exemplar emprestado retorna 200."""
    obra = await obra_factory(db_session, titulo="Obra CIN-001")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, codigo_qr="QR-CIN-001")
    leitor = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)

    response = await client.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )
    assert response.status_code == 200


# ─── CIN-E2E-002 ─────────────────────────────────────────────────────────────

async def test_cin_e2e_002_resposta_tem_status_devolvido_e_data_devolucao(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CIN-E2E-002 — Resposta contém status='devolvido' e data_devolucao preenchida."""
    obra = await obra_factory(db_session, titulo="Obra CIN-002")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, codigo_qr="QR-CIN-002")
    leitor = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)

    response = await client.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "devolvido"
    assert data["data_devolucao"] is not None


# ─── CIN-E2E-003 ─────────────────────────────────────────────────────────────

async def test_cin_e2e_003_exemplar_volta_para_disponivel(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CIN-E2E-003 — Estado do exemplar é 'disponivel' após a devolução."""
    from sqlalchemy import text

    obra = await obra_factory(db_session, titulo="Obra CIN-003")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, codigo_qr="QR-CIN-003", estado="emprestado")
    leitor = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)

    resp = await client.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )
    assert resp.status_code == 200

    # Verifica o estado via SQL bruto na mesma conexão/SAVEPOINT.
    result = await db_session.execute(
        text("SELECT estado FROM exemplar WHERE id = :id"),
        {"id": exemplar.id},
    )
    assert result.scalar_one() == "disponivel"


# ─── CIN-E2E-004 ─────────────────────────────────────────────────────────────

async def test_cin_e2e_004_resolve_emprestimo_apenas_pelo_qr(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CIN-E2E-004 — Sistema resolve o empréstimo ativo apenas pelo codigo_qr, sem emprestimo_id."""
    obra = await obra_factory(db_session, titulo="Obra CIN-004")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, codigo_qr="QR-CIN-004", estado="emprestado")
    leitor = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)

    # Envia apenas codigo_qr — nenhum emprestimo_id
    response = await client.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "devolvido"


# ─── CIN-E2E-005 ─────────────────────────────────────────────────────────────

async def test_cin_e2e_005_qr_sem_emprestimo_ativo_retorna_404(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CIN-E2E-005 — QR Code de exemplar sem empréstimo ativo retorna 404."""
    obra = await obra_factory(db_session, titulo="Obra CIN-005")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, codigo_qr="QR-CIN-005")

    # Nenhum empréstimo criado para este exemplar
    response = await client.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )
    assert response.status_code == 404


# ─── CIN-E2E-006 ─────────────────────────────────────────────────────────────

async def test_cin_e2e_006_devolucao_ativa_reserva_aguardando(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CIN-E2E-006 — Reserva 'aguardando' fica com status 'disponivel' após devolução."""
    obra = await obra_factory(db_session, titulo="Obra CIN-006")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, codigo_qr="QR-CIN-006", estado="emprestado")
    leitor_a = await leitor_factory(db_session, nome="Leitor A CIN-006")
    leitor_b = await leitor_factory(db_session, nome="Leitor B CIN-006")

    # Empréstimo ativo do leitor A
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)

    # Reserva do leitor B (aguardando)
    reserva = ReservaModel(
        id=uuid.uuid4(),
        obra_id=obra.id,
        leitor_id=leitor_b.id,
        status="aguardando",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(reserva)
    await db_session.flush()
    await db_session.refresh(reserva)

    # Devolução do leitor A
    resp = await client.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )
    assert resp.status_code == 200

    # Verifica a reserva do leitor B via GET (se endpoint disponível) ou via db
    await db_session.refresh(reserva)
    assert reserva.status == "disponivel", (
        f"Reserva deveria ser 'disponivel', obtido '{reserva.status}'"
    )


# ─── CIN-E2E-007 ─────────────────────────────────────────────────────────────

async def test_cin_e2e_007_sem_token_retorna_401(client: AsyncClient) -> None:
    """CIN-E2E-007 — POST /api/emprestimos/devolver-por-qr sem token JWT retorna 401."""
    response = await client.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": "QR-SEM-TOKEN"},
    )
    assert response.status_code == 401


# ─── CIN-E2E-008 ─────────────────────────────────────────────────────────────

async def test_cin_e2e_008_devolver_por_id_retorna_200(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CIN-E2E-008 — POST /api/emprestimos/{id}/devolver (fluxo alternativo) retorna 200."""
    obra = await obra_factory(db_session, titulo="Obra CIN-008")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, codigo_qr="QR-CIN-008", estado="emprestado")
    leitor = await leitor_factory(db_session)
    emprestimo = await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)

    response = await client.post(
        f"/api/emprestimos/{emprestimo.id}/devolver",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "devolvido"


# ─── CIN-E2E-009 ─────────────────────────────────────────────────────────────

async def test_cin_e2e_009_devolver_por_id_inexistente_retorna_404(
    client: AsyncClient,
    auth_headers_operador: dict,
) -> None:
    """CIN-E2E-009 — POST /api/emprestimos/{id}/devolver com ID inexistente retorna 404."""
    response = await client.post(
        f"/api/emprestimos/{uuid.uuid4()}/devolver",
        headers=auth_headers_operador,
    )
    assert response.status_code == 404


# ─── CIN-E2E-010 ─────────────────────────────────────────────────────────────

async def test_cin_e2e_010_data_devolucao_proxima_ao_momento_do_teste(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """CIN-E2E-010 — data_devolucao retornada é próxima ao momento do teste."""
    obra = await obra_factory(db_session, titulo="Obra CIN-010")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, codigo_qr="QR-CIN-010", estado="emprestado")
    leitor = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)

    before = datetime.now(tz=timezone.utc)
    response = await client.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )
    after = datetime.now(tz=timezone.utc)

    assert response.status_code == 200
    data_devolucao_str = response.json()["data_devolucao"]
    data_devolucao = datetime.fromisoformat(data_devolucao_str)
    if data_devolucao.tzinfo is None:
        data_devolucao = data_devolucao.replace(tzinfo=timezone.utc)

    assert data_devolucao >= before
    assert data_devolucao <= after
