"""
Testes E2E — Sub-Tarefa 5: Log de Notificações (US-018)
Casos: LOG-E2E-001 a LOG-E2E-008

Cobre:
  - Após check-in com reserva aguardando, notificacao_log tem campos obrigatórios
  - Registro de sucesso: status='enviado' e erro=null
  - Registro contém leitor_id, template, timestamp
  - Registro de erro: status='erro' e erro com mensagem da falha
  - notificacao_log não contém campo com texto completo da mensagem enviada
  - Job de lembretes também gera registro em notificacao_log
  - Log gravado mesmo quando envio falhou (independência do check-in)
  - timestamp do registro é próximo ao momento do teste (não nulo, não futuro)

Verificações são feitas via db_session diretamente.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.notificacao_log import NotificacaoLogModel
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


# ─── LOG-E2E-001 a LOG-E2E-003 ────────────────────────────────────────────────

async def test_log_e2e_001_checkin_com_reserva_cria_log_com_campos_obrigatorios(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LOG-E2E-001 — Check-in com reserva aguardando cria registro em notificacao_log com campos obrigatórios."""
    obra = await obra_factory(db_session, titulo="Obra LOG-001")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session, telefone="11999991001")
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)
    await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_b.id)

    await client_com_stub.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )

    result = await db_session.execute(
        select(NotificacaoLogModel)
        .where(NotificacaoLogModel.leitor_id == leitor_b.id)
        .order_by(NotificacaoLogModel.timestamp.desc())
        .limit(1)
    )
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.leitor_id is not None
    assert log.template == "reserva_disponivel"
    assert log.status in ("enviado", "erro")
    assert log.timestamp is not None


async def test_log_e2e_002_registro_de_sucesso_tem_status_enviado_e_erro_null(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LOG-E2E-002 — Registro de sucesso tem status='enviado' e erro=null."""
    obra = await obra_factory(db_session, titulo="Obra LOG-002")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session, telefone="11999991002")
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)
    await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_b.id)

    await client_com_stub.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )

    result = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.leitor_id == leitor_b.id,
            NotificacaoLogModel.template == "reserva_disponivel",
            NotificacaoLogModel.status == "enviado",
        )
    )
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.erro is None


async def test_log_e2e_003_registro_contem_leitor_id_template_timestamp(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LOG-E2E-003 — Registro contém leitor_id, template, timestamp preenchidos."""
    obra = await obra_factory(db_session, titulo="Obra LOG-003")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session, telefone="11999991003")
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)
    await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_b.id)

    await client_com_stub.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )

    result = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.leitor_id == leitor_b.id,
        )
    )
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.leitor_id == leitor_b.id
    assert log.template is not None and log.template != ""
    assert log.timestamp is not None


# ─── LOG-E2E-004 ──────────────────────────────────────────────────────────────

async def test_log_e2e_004_registro_de_erro_tem_status_erro_e_mensagem(
    db_session: AsyncSession,
) -> None:
    """LOG-E2E-004 — Registro de erro tem status='erro' e campo 'erro' com mensagem da falha."""
    obra = await obra_factory(db_session, titulo="Obra LOG-004")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session, telefone="11999991004")
    await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=_amanha_utc(),
    )

    log_repo = SQLAlchemyNotificacaoLogRepository(db_session)
    stub_falha = NotificacaoGatewayLoggingStub(
        log_repo=log_repo,
        raise_on_first=True,
        error_message="Timeout ao conectar",
    )
    use_case = EnviarLembretesUseCase(
        emprestimo_repo=SQLAlchemyEmprestimoRepository(db_session),
        leitor_repo=SQLAlchemyLeitorRepository(db_session),
        exemplar_repo=SQLAlchemyExemplarRepository(db_session),
        obra_repo=SQLAlchemyObraRepository(db_session),
        notificacao_gateway=stub_falha,
    )

    await use_case.execute()

    result = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.leitor_id == leitor.id,
            NotificacaoLogModel.status == "erro",
        )
    )
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.status == "erro"
    assert log.erro is not None
    assert "Timeout" in log.erro


# ─── LOG-E2E-005 ──────────────────────────────────────────────────────────────

async def test_log_e2e_005_notificacao_log_nao_contem_texto_mensagem(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LOG-E2E-005 — notificacao_log não contém campo com texto completo da mensagem enviada."""
    obra = await obra_factory(db_session, titulo="Obra LOG-005")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session, telefone="11999991005")
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)
    await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_b.id)

    await client_com_stub.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )

    result = await db_session.execute(
        select(NotificacaoLogModel).where(NotificacaoLogModel.leitor_id == leitor_b.id)
    )
    log = result.scalar_one_or_none()
    assert log is not None

    # O modelo deve ter apenas os campos de metadados (sem mensagem completa)
    columns = [c.key for c in NotificacaoLogModel.__table__.columns]
    assert "mensagem" not in columns
    assert "conteudo" not in columns
    assert "texto" not in columns
    # Confirma que contém apenas metadados
    assert "template" in columns
    assert "status" in columns
    assert "leitor_id" in columns
    assert "timestamp" in columns


# ─── LOG-E2E-006 ──────────────────────────────────────────────────────────────

async def test_log_e2e_006_job_lembretes_gera_registro_em_notificacao_log(
    db_session: AsyncSession,
) -> None:
    """LOG-E2E-006 — Job de lembretes (US-017) também gera registro em notificacao_log."""
    obra = await obra_factory(db_session, titulo="Obra LOG-006")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session, telefone="11999991006")
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

    await use_case.execute()

    result = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.leitor_id == leitor.id,
            NotificacaoLogModel.template == "lembrete_devolucao",
        )
    )
    assert result.scalar_one_or_none() is not None


# ─── LOG-E2E-007 ──────────────────────────────────────────────────────────────

async def test_log_e2e_007_log_gravado_independente_do_sucesso_do_checkin(
    client_com_stub_falho: tuple[AsyncClient, AsyncSession],
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LOG-E2E-007 — Log gravado mesmo quando check-in retorna 200 e envio falhou.

    Usa client_com_stub_falho que injeta um stub configurado para lançar exceção
    na primeira chamada a enviar(). O test body apenas monta dados e faz asserções —
    a composição da infraestrutura está no conftest.
    """
    client, session = client_com_stub_falho  # session == db_session (mesma instância)

    obra = await obra_factory(db_session, titulo="Obra LOG-007")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session, telefone="11999991007")
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)
    await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_b.id)

    response = await client.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )

    # Check-in retorna 200 (falha de notificação não bloqueia a operação principal)
    assert response.status_code == 200
    assert response.json()["status"] == "devolvido"

    # Log de erro gravado na mesma sessão compartilhada (visível via db_session)
    result = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.leitor_id == leitor_b.id,
            NotificacaoLogModel.status == "erro",
        )
    )
    assert result.scalar_one_or_none() is not None


# ─── LOG-E2E-008 ──────────────────────────────────────────────────────────────

async def test_log_e2e_008_timestamp_proximo_ao_momento_do_teste(
    client_com_stub: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """LOG-E2E-008 — timestamp do registro é próximo ao momento do teste (não nulo, não futuro)."""
    obra = await obra_factory(db_session, titulo="Obra LOG-008")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor_a = await leitor_factory(db_session)
    leitor_b = await leitor_factory(db_session, telefone="11999991008")
    await emprestimo_factory(db_session, exemplar_id=exemplar.id, leitor_id=leitor_a.id)
    await reserva_factory(db_session, obra_id=obra.id, leitor_id=leitor_b.id)

    before = datetime.now(timezone.utc)

    await client_com_stub.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )

    after = datetime.now(timezone.utc) + timedelta(seconds=5)

    result = await db_session.execute(
        select(NotificacaoLogModel).where(NotificacaoLogModel.leitor_id == leitor_b.id)
    )
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.timestamp is not None

    # O timestamp deve ser timezone-aware para comparação
    ts = log.timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    assert ts >= before - timedelta(seconds=5)  # tolerância de 5s antes
    assert ts <= after
