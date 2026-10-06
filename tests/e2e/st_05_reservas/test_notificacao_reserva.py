"""
Testes E2E — Sub-Tarefa 3: Notificação de Reserva Disponível via Check-In (US-016)
Casos: NTF-E2E-001 a NTF-E2E-008

Cobre:
  - Após check-in com reserva aguardando, reserva passa para status "disponivel"
  - Registro criado em notificacao_log com template "reserva_disponivel"
  - Leitor sem telefone: devolução ocorre normalmente (200), sem registro de erro no log
  - Check-in sem reserva aguardando: devolução normal, sem notificação
  - Fluxo alternativo POST /api/emprestimos/{id}/devolver também aciona notificação
  - Quando múltiplas reservas, apenas o primeiro da fila (menor created_at) é notificado
  - POST /api/emprestimos/devolver-por-qr sem token retorna 401

Usa client_com_stub que injeta NotificacaoGatewayLoggingStub para verificar notificacao_log.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.notificacao_log import NotificacaoLogModel
from app.adapters.repositories.models.reserva import ReservaModel
from tests.e2e.st_05_reservas.conftest import (
    emprestimo_factory,
    exemplar_factory,
    leitor_factory,
    leitor_sem_telefone_factory,
    obra_factory,
    reserva_factory,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ─── NTF-E2E-001 ──────────────────────────────────────────────────────────────

async def test_ntf_e2e_001_checkin_com_reserva_aguardando_ativa_reserva(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """NTF-E2E-001 — Após check-in com reserva aguardando, reserva fica com status 'disponivel'."""
    obra = await obra_factory(db_session, titulo="Obra NTF-001")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session, telefone="11999990001")
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)
    reserva = await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_b.id)

    response = await client_com_stub.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "devolvido"

    # Verifica que a reserva foi ativada
    result = await db_session.execute(
        select(ReservaModel).where(ReservaModel.id == reserva.id)
    )
    reserva_atualizada = result.scalar_one_or_none()
    assert reserva_atualizada is not None
    assert reserva_atualizada.status == "disponivel"


# ─── NTF-E2E-002 ──────────────────────────────────────────────────────────────

async def test_ntf_e2e_002_checkin_cria_registro_em_notificacao_log(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """NTF-E2E-002 — Registro em notificacao_log criado com template='reserva_disponivel' após check-in."""
    obra = await obra_factory(db_session, titulo="Obra NTF-002")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session, telefone="11999990002")
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)
    await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_b.id)

    response = await client_com_stub.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )

    assert response.status_code == 200

    result = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.leitor_id == leitor_b.id,
            NotificacaoLogModel.template == "reserva_disponivel",
        )
    )
    log_entries = result.scalars().all()
    assert len(log_entries) >= 1
    assert log_entries[0].status in ("enviado", "erro")


# ─── NTF-E2E-003 ──────────────────────────────────────────────────────────────

async def test_ntf_e2e_003_leitor_sem_telefone_devolucao_retorna_200(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """NTF-E2E-003 — Leitor sem telefone: POST /api/emprestimos/devolver-por-qr retorna 200."""
    obra = await obra_factory(db_session, titulo="Obra NTF-003")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_com_livro = await leitor_factory(db_session)
    leitor_sem_fone = await leitor_sem_telefone_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_com_livro.id)
    await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_sem_fone.id)

    response = await client_com_stub.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "devolvido"


# ─── NTF-E2E-004 ──────────────────────────────────────────────────────────────

async def test_ntf_e2e_004_leitor_sem_telefone_nenhum_erro_em_notificacao_log(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """NTF-E2E-004 — Leitor sem telefone: nenhum registro criado em notificacao_log com status='erro'."""
    obra = await obra_factory(db_session, titulo="Obra NTF-004")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_com_livro = await leitor_factory(db_session)
    leitor_sem_fone = await leitor_sem_telefone_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_com_livro.id)
    await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_sem_fone.id)

    await client_com_stub.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )

    # Verifica que a reserva avançou para "disponivel" (mas sem notificação)
    result_reserva = await db_session.execute(
        select(ReservaModel).where(
            ReservaModel.obra_id == obra.id,
            ReservaModel.leitor_id == leitor_sem_fone.id,
        )
    )
    reserva = result_reserva.scalar_one_or_none()
    assert reserva is not None
    assert reserva.status == "disponivel"

    # Nenhum registro de erro para este leitor
    result_log = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.leitor_id == leitor_sem_fone.id,
            NotificacaoLogModel.status == "erro",
        )
    )
    assert result_log.scalar_one_or_none() is None


# ─── NTF-E2E-005 ──────────────────────────────────────────────────────────────

async def test_ntf_e2e_005_checkin_sem_reserva_aguardando_devolucao_normal(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """NTF-E2E-005 — Check-in sem reserva aguardando: devolução ocorre normalmente."""
    obra = await obra_factory(db_session, titulo="Obra NTF-005")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor.id)
    # Sem reserva criada para esta obra

    response = await client_com_stub.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "devolvido"

    # Nenhuma notificação disparada
    result = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.template == "reserva_disponivel",
        )
    )
    assert result.scalar_one_or_none() is None


# ─── NTF-E2E-006 ──────────────────────────────────────────────────────────────

async def test_ntf_e2e_006_fluxo_alternativo_devolver_por_id_aciona_notificacao(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """NTF-E2E-006 — POST /api/emprestimos/{id}/devolver também aciona notificação de reserva."""
    obra = await obra_factory(db_session, titulo="Obra NTF-006")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session, telefone="11999990006")
    emprestimo = await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)
    reserva = await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_b.id)

    response = await client_com_stub.post(
        f"/api/emprestimos/{emprestimo.id}/devolver",
        headers=auth_headers_operador,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "devolvido"

    # Reserva ativada
    result_reserva = await db_session.execute(
        select(ReservaModel).where(ReservaModel.id == reserva.id)
    )
    reserva_atualizada = result_reserva.scalar_one_or_none()
    assert reserva_atualizada is not None
    assert reserva_atualizada.status == "disponivel"

    # Log criado
    result_log = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.leitor_id == leitor_b.id,
            NotificacaoLogModel.template == "reserva_disponivel",
        )
    )
    assert result_log.scalar_one_or_none() is not None


# ─── NTF-E2E-007 ──────────────────────────────────────────────────────────────

async def test_ntf_e2e_007_apenas_primeiro_da_fila_e_notificado(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """NTF-E2E-007 — Quando há múltiplas reservas, apenas o primeiro da fila é notificado."""
    now = datetime.now(timezone.utc)
    obra = await obra_factory(db_session, titulo="Obra NTF-007")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session, telefone="11999990007")
    leitor_c = await leitor_factory(db_session, telefone="11999990008")
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)

    # leitor_b é o primeiro na fila (created_at menor)
    reserva_b = await reserva_factory(
        db_session,
        obra_id=obra.id,
        leitor_id=leitor_b.id,
        created_at=now - timedelta(minutes=10),
    )
    reserva_c = await reserva_factory(
        db_session,
        obra_id=obra.id,
        leitor_id=leitor_c.id,
        created_at=now - timedelta(minutes=5),
    )

    await client_com_stub.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )

    # Apenas a reserva de leitor_b deve estar "disponivel"
    result_b = await db_session.execute(
        select(ReservaModel).where(ReservaModel.id == reserva_b.id)
    )
    result_c = await db_session.execute(
        select(ReservaModel).where(ReservaModel.id == reserva_c.id)
    )
    assert result_b.scalar_one().status == "disponivel"
    assert result_c.scalar_one().status == "aguardando"

    # Apenas 1 registro de notificação (para leitor_b)
    result_log = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.template == "reserva_disponivel",
        )
    )
    logs = result_log.scalars().all()
    assert len(logs) == 1
    assert logs[0].leitor_id == leitor_b.id


# ─── NTF-E2E-008 ──────────────────────────────────────────────────────────────

async def test_ntf_e2e_008_devolver_por_qr_sem_token_retorna_401(
    client_com_stub: AsyncClient,
) -> None:
    """NTF-E2E-008 — POST /api/emprestimos/devolver-por-qr sem token JWT retorna 401."""
    response = await client_com_stub.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": "QR-SEM-TOKEN"},
    )

    assert response.status_code == 401
