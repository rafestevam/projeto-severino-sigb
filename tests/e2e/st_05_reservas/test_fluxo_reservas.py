"""
Testes E2E — Sub-Tarefa 6: Fluxo Completo de Reservas e Notificações (Happy Path)
Casos: FLOW-R-001 a FLOW-R-004

Cobre:
  - FLOW-R-001: Jornada completa — devolução ativa reserva e gera log, reserva pode ser
    cancelada em seguida.
  - FLOW-R-002: Fila com 2 reservantes — devolução ativa apenas o primeiro da fila.
  - FLOW-R-003: Cancelamento libera nova reserva pelo mesmo leitor.
  - FLOW-R-004: Fluxo de lembrete D-1 com verificação de log via use case direto.

Princípio de isolamento: setup de estado (obra, exemplar, leitores, empréstimo, reserva)
é feito via factories diretamente no banco, evitando dependências entre requisições HTTP
na mesma transação de teste. Requisições HTTP exercitam apenas as ações sob teste.
"""

from __future__ import annotations

import uuid as uuid_mod
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.notificacao_log import NotificacaoLogModel
from app.adapters.repositories.models.reserva import ReservaModel
from app.adapters.repositories.sqlalchemy_emprestimo_repository import (
    SQLAlchemyEmprestimoRepository,
)
from app.adapters.repositories.sqlalchemy_exemplar_repository import (
    SQLAlchemyExemplarRepository,
)
from app.adapters.repositories.sqlalchemy_leitor_repository import (
    SQLAlchemyLeitorRepository,
)
from app.adapters.repositories.sqlalchemy_notificacao_log_repository import (
    SQLAlchemyNotificacaoLogRepository,
)
from app.adapters.repositories.sqlalchemy_obra_repository import (
    SQLAlchemyObraRepository,
)
from app.use_cases.enviar_lembretes import EnviarLembretesUseCase
from tests.e2e.st_05_reservas.conftest import (
    emprestimo_factory,
    exemplar_factory,
    leitor_factory,
    obra_factory,
    reserva_factory,
)
from tests.infrastructure.notificacao_gateway_logging_stub import (
    NotificacaoGatewayLoggingStub,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _amanha_utc() -> datetime:
    amanha = date.today() + timedelta(days=1)
    return datetime(amanha.year, amanha.month, amanha.day, 12, 0, 0, tzinfo=timezone.utc)


# ─── FLOW-R-001 ───────────────────────────────────────────────────────────────

async def test_flow_r_001_jornada_completa_leitor_reservante(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """
    FLOW-R-001 — Jornada completa: devolução → reserva ativada → log → cancelamento.

    Setup via factories (visível para todos os requests HTTP).
    Passos HTTP:
      1. devolver-por-qr     → 200, status="devolvido"
      2. verificar reserva   → status="disponivel" via db_session
      3. verificar log       → notificacao_log tem registro "reserva_disponivel"
      4. cancelar reserva    → DELETE retorna status="expirada"
    """
    # ── Setup via factories ───────────────────────────────────────────────────
    obra = await obra_factory(db_session, titulo="Obra FLOW-001")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session, telefone="11999990101")
    leitor_b = await leitor_factory(db_session, telefone="11999990102")
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)
    reserva = await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_b.id)

    # ── Passo 1: Devolução pelo leitor_A ─────────────────────────────────────
    resp_devolucao = await client_com_stub.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )
    assert resp_devolucao.status_code == 200
    assert resp_devolucao.json()["status"] == "devolvido"

    # ── Passo 2: Reserva do leitor_B ativada ─────────────────────────────────
    await db_session.refresh(reserva)
    assert reserva.status == "disponivel"

    # ── Passo 3: Notificação registrada ──────────────────────────────────────
    result_log = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.leitor_id == leitor_b.id,
            NotificacaoLogModel.template == "reserva_disponivel",
        )
    )
    log = result_log.scalar_one_or_none()
    assert log is not None
    assert log.status == "enviado"
    assert log.leitor_id == leitor_b.id

    # ── Passo 4: Cancelar reserva do leitor_B ────────────────────────────────
    resp_cancel = await client_com_stub.delete(
        f"/api/reservas/{reserva.id}",
        headers=auth_headers_operador,
    )
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "expirada"


# ─── FLOW-R-002 ───────────────────────────────────────────────────────────────

async def test_flow_r_002_fila_com_multiplos_reservantes(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """
    FLOW-R-002 — Fila com 2 reservantes: devolução ativa apenas o primeiro.

    Setup via factories. Único request HTTP: devolver-por-qr.
    """
    now = datetime.now(timezone.utc)

    obra = await obra_factory(db_session, titulo="Obra FLOW-002")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session, telefone="11999990200")
    leitor_c = await leitor_factory(db_session, telefone="11999990201")
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

    await db_session.refresh(reserva_b)
    await db_session.refresh(reserva_c)
    assert reserva_b.status == "disponivel"
    assert reserva_c.status == "aguardando"

    result_log = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.template == "reserva_disponivel",
        )
    )
    logs = result_log.scalars().all()
    assert len(logs) == 1
    assert logs[0].leitor_id == leitor_b.id


# ─── FLOW-R-003 ───────────────────────────────────────────────────────────────

async def test_flow_r_003_cancelamento_libera_nova_reserva(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """
    FLOW-R-003 — Reserva cancelada não bloqueia nova reserva pelo mesmo leitor.

    Setup via factories: reserva_b criada como "aguardando".
    Passo 1 HTTP: DELETE cancela reserva_b → status="expirada".
    Passo 2 HTTP: POST cria nova reserva para o mesmo leitor → 201, posicao_fila=1.
    """
    obra = await obra_factory(db_session, titulo="Obra FLOW-003")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session)
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)

    # Reserva existente criada via factory (visível para os requests HTTP)
    reserva = await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_b.id)

    # ── Passo 1: Cancela a reserva ───────────────────────────────────────────
    resp_cancel = await client_com_stub.delete(
        f"/api/reservas/{reserva.id}",
        headers=auth_headers_operador,
    )
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "expirada"

    # ── Passo 2: Nova reserva pelo mesmo leitor ───────────────────────────────
    # A reserva expirada não conta como ativa → 201 esperado
    resp_nova = await client_com_stub.post(
        "/api/reservas",
        json={"obra_id": str(obra.id), "leitor_id": str(leitor_b.id)},
        headers=auth_headers_operador,
    )
    assert resp_nova.status_code == 201
    assert resp_nova.json()["status"] == "aguardando"
    assert resp_nova.json()["posicao_fila"] == 1


# ─── FLOW-R-004 ───────────────────────────────────────────────────────────────

async def test_flow_r_004_lembrete_d1_com_log(
    db_session: AsyncSession,
) -> None:
    """
    FLOW-R-004 — Lembrete D-1 com verificação de log via use case direto.

    Instancia EnviarLembretesUseCase com repositórios reais e stub de logging.
    Nenhum request HTTP — o job é executado diretamente.
    """
    obra = await obra_factory(db_session, titulo="Obra FLOW-004")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session, telefone="11999990400")
    await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=_amanha_utc(),
    )

    log_repo = SQLAlchemyNotificacaoLogRepository(db_session)
    stub = NotificacaoGatewayLoggingStub(log_repo=log_repo)
    use_case = EnviarLembretesUseCase(
        emprestimo_repo=SQLAlchemyEmprestimoRepository(db_session),
        leitor_repo=SQLAlchemyLeitorRepository(db_session),
        exemplar_repo=SQLAlchemyExemplarRepository(db_session),
        obra_repo=SQLAlchemyObraRepository(db_session),
        notificacao_gateway=stub,
    )

    resultado = await use_case.execute()

    assert resultado == 1

    result = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.leitor_id == leitor.id,
            NotificacaoLogModel.template == "lembrete_devolucao",
            NotificacaoLogModel.status == "enviado",
        )
    )
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.leitor_id == leitor.id
