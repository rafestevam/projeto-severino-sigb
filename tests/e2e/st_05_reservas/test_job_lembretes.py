"""
Testes E2E — Sub-Tarefa 4: Job de Lembretes D-1 (US-017)
Casos: LEM-E2E-001 a LEM-E2E-010

Cobre:
  - EnviarLembretesUseCase.execute() identifica empréstimos com data_prevista = amanhã
  - Retorna contagem correta de lembretes enviados
  - Leitores sem telefone são ignorados silenciosamente
  - Empréstimos devolvidos não recebem lembrete
  - Empréstimos com data_prevista = hoje, hoje+2 ou ontem não recebem lembrete D-1
  - Múltiplos empréstimos vencendo amanhã são todos processados
  - Falha de gateway é registrada sem interromper o loop
  - Segunda execução no mesmo banco (idempotência do dia)

Os testes instanciam EnviarLembretesUseCase diretamente com repositórios SQLAlchemy
reais e NotificacaoGatewayLoggingStub, controlando datas via emprestimo_factory.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
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
from tests.infrastructure.notificacao_gateway_logging_stub import (
    NotificacaoGatewayLoggingStub,
)
from app.use_cases.enviar_lembretes import EnviarLembretesUseCase
from tests.e2e.st_05_reservas.conftest import (
    emprestimo_factory,
    exemplar_factory,
    leitor_factory,
    leitor_sem_telefone_factory,
    obra_factory,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _amanha_utc() -> datetime:
    """Retorna datetime no início do dia de amanhã em UTC (para data_prevista)."""
    amanha = date.today() + timedelta(days=1)
    return datetime(amanha.year, amanha.month, amanha.day, 12, 0, 0, tzinfo=timezone.utc)


def _hoje_utc() -> datetime:
    hoje = date.today()
    return datetime(hoje.year, hoje.month, hoje.day, 12, 0, 0, tzinfo=timezone.utc)


def _ontem_utc() -> datetime:
    ontem = date.today() - timedelta(days=1)
    return datetime(ontem.year, ontem.month, ontem.day, 12, 0, 0, tzinfo=timezone.utc)


def _depois_de_amanha_utc() -> datetime:
    depois = date.today() + timedelta(days=2)
    return datetime(depois.year, depois.month, depois.day, 12, 0, 0, tzinfo=timezone.utc)


async def _build_use_case(
    db_session: AsyncSession,
    raise_on_first: bool = False,
    error_message: str = "Timeout ao conectar",
) -> EnviarLembretesUseCase:
    """Instancia EnviarLembretesUseCase com repositórios reais e stub de notificação."""
    log_repo = SQLAlchemyNotificacaoLogRepository(db_session)
    stub = NotificacaoGatewayLoggingStub(
        log_repo=log_repo,
        raise_on_first=raise_on_first,
        error_message=error_message,
    )
    return EnviarLembretesUseCase(
        emprestimo_repo=SQLAlchemyEmprestimoRepository(db_session),
        leitor_repo=SQLAlchemyLeitorRepository(db_session),
        exemplar_repo=SQLAlchemyExemplarRepository(db_session),
        obra_repo=SQLAlchemyObraRepository(db_session),
        notificacao_gateway=stub,
    )


# ─── LEM-E2E-001 ──────────────────────────────────────────────────────────────

async def test_lem_e2e_001_emprestimo_d1_com_telefone_recebe_lembrete(
    db_session: AsyncSession,
) -> None:
    """LEM-E2E-001 — Empréstimo com data_prevista = amanhã e leitor com telefone recebe lembrete."""
    obra = await obra_factory(db_session, titulo="Obra LEM-001")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session, telefone="11999990001")
    await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=_amanha_utc(),
    )

    use_case = await _build_use_case(db_session)
    resultado = await use_case.execute()

    assert resultado >= 1

    result = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.leitor_id == leitor.id,
            NotificacaoLogModel.template == "lembrete_devolucao",
        )
    )
    assert result.scalar_one_or_none() is not None


# ─── LEM-E2E-002 ──────────────────────────────────────────────────────────────

async def test_lem_e2e_002_retorna_contagem_de_lembretes_enviados(
    db_session: AsyncSession,
) -> None:
    """LEM-E2E-002 — Use Case retorna contagem igual ao número de lembretes enviados."""
    obra = await obra_factory(db_session, titulo="Obra LEM-002")
    exemplar1 = await exemplar_factory(db_session, obra_id=obra.id)
    exemplar2 = await exemplar_factory(db_session, obra_id=obra.id)
    leitor1 = await leitor_factory(db_session, telefone="11999990010")
    leitor2 = await leitor_factory(db_session, telefone="11999990011")
    await emprestimo_factory(
        db_session, exemplar_id=exemplar1.id, leitor_id=leitor1.id, data_prevista=_amanha_utc()
    )
    await emprestimo_factory(
        db_session, exemplar_id=exemplar2.id, leitor_id=leitor2.id, data_prevista=_amanha_utc()
    )

    use_case = await _build_use_case(db_session)
    resultado = await use_case.execute()

    assert resultado == 2


# ─── LEM-E2E-003 ──────────────────────────────────────────────────────────────

async def test_lem_e2e_003_leitor_sem_telefone_e_ignorado_silenciosamente(
    db_session: AsyncSession,
) -> None:
    """LEM-E2E-003 — Empréstimo com data_prevista = amanhã e leitor sem telefone é ignorado."""
    obra = await obra_factory(db_session, titulo="Obra LEM-003")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_sem_telefone_factory(db_session)
    await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=_amanha_utc(),
    )

    use_case = await _build_use_case(db_session)
    resultado = await use_case.execute()

    assert resultado == 0

    result = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.leitor_id == leitor.id,
        )
    )
    assert result.scalar_one_or_none() is None


# ─── LEM-E2E-004 ──────────────────────────────────────────────────────────────

async def test_lem_e2e_004_emprestimo_devolvido_nao_recebe_lembrete(
    db_session: AsyncSession,
) -> None:
    """LEM-E2E-004 — Empréstimo com status='devolvido' e data_prevista=amanhã não recebe lembrete."""
    obra = await obra_factory(db_session, titulo="Obra LEM-004")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session, telefone="11999990020")
    await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=_amanha_utc(),
        status="devolvido",
    )

    use_case = await _build_use_case(db_session)
    resultado = await use_case.execute()

    assert resultado == 0


# ─── LEM-E2E-005 ──────────────────────────────────────────────────────────────

async def test_lem_e2e_005_emprestimo_com_vencimento_hoje_nao_recebe_lembrete(
    db_session: AsyncSession,
) -> None:
    """LEM-E2E-005 — Empréstimo com data_prevista=hoje (vence hoje) não recebe lembrete."""
    obra = await obra_factory(db_session, titulo="Obra LEM-005")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session, telefone="11999990030")
    await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=_hoje_utc(),
    )

    use_case = await _build_use_case(db_session)
    resultado = await use_case.execute()

    assert resultado == 0


# ─── LEM-E2E-006 ──────────────────────────────────────────────────────────────

async def test_lem_e2e_006_emprestimo_com_vencimento_depois_de_amanha_nao_recebe_lembrete(
    db_session: AsyncSession,
) -> None:
    """LEM-E2E-006 — Empréstimo com data_prevista=hoje+2 não recebe lembrete D-1."""
    obra = await obra_factory(db_session, titulo="Obra LEM-006")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session, telefone="11999990040")
    await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=_depois_de_amanha_utc(),
    )

    use_case = await _build_use_case(db_session)
    resultado = await use_case.execute()

    assert resultado == 0


# ─── LEM-E2E-007 ──────────────────────────────────────────────────────────────

async def test_lem_e2e_007_emprestimo_vencido_ontem_nao_recebe_lembrete(
    db_session: AsyncSession,
) -> None:
    """LEM-E2E-007 — Empréstimo com data_prevista=ontem (já vencido) não recebe lembrete D-1."""
    obra = await obra_factory(db_session, titulo="Obra LEM-007")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session, telefone="11999990050")
    await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=_ontem_utc(),
    )

    use_case = await _build_use_case(db_session)
    resultado = await use_case.execute()

    assert resultado == 0


# ─── LEM-E2E-008 ──────────────────────────────────────────────────────────────

async def test_lem_e2e_008_multiplos_emprestimos_d1_sao_todos_processados(
    db_session: AsyncSession,
) -> None:
    """LEM-E2E-008 — Múltiplos empréstimos com vencimento amanhã são todos processados."""
    obra = await obra_factory(db_session, titulo="Obra LEM-008")
    exemplares = [
        await exemplar_factory(db_session, obra_id=obra.id)
        for _ in range(3)
    ]
    leitores = [
        await leitor_factory(db_session, telefone=f"1199999{i:04d}")
        for i in range(100, 103)
    ]
    for exemplar, leitor in zip(exemplares, leitores):
        await emprestimo_factory(
            db_session,
            exemplar_id=exemplar.id,
            leitor_id=leitor.id,
            data_prevista=_amanha_utc(),
        )

    use_case = await _build_use_case(db_session)
    resultado = await use_case.execute()

    assert resultado == 3

    for leitor in leitores:
        result = await db_session.execute(
            select(NotificacaoLogModel).where(
                NotificacaoLogModel.leitor_id == leitor.id,
                NotificacaoLogModel.template == "lembrete_devolucao",
            )
        )
        assert result.scalar_one_or_none() is not None


# ─── LEM-E2E-009 ──────────────────────────────────────────────────────────────

async def test_lem_e2e_009_falha_gateway_registrada_sem_interromper_loop(
    db_session: AsyncSession,
) -> None:
    """LEM-E2E-009 — Falha de gateway para um empréstimo é registrada sem interromper o loop."""
    obra = await obra_factory(db_session, titulo="Obra LEM-009")
    exemplar_a = await exemplar_factory(db_session, obra_id=obra.id)
    exemplar_b = await exemplar_factory(db_session, obra_id=obra.id)
    leitor_a = await leitor_factory(db_session, telefone="11999990200")
    leitor_b = await leitor_factory(db_session, telefone="11999990201")
    await emprestimo_factory(
        db_session,
        exemplar_id=exemplar_a.id,
        leitor_id=leitor_a.id,
        data_prevista=_amanha_utc(),
    )
    await emprestimo_factory(
        db_session,
        exemplar_id=exemplar_b.id,
        leitor_id=leitor_b.id,
        data_prevista=_amanha_utc(),
    )

    # Stub que falha na primeira chamada
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

    resultado = await use_case.execute()

    # Um enviado, um com falha
    assert resultado == 1

    result_erro = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.status == "erro",
            NotificacaoLogModel.template == "lembrete_devolucao",
        )
    )
    result_enviado = await db_session.execute(
        select(NotificacaoLogModel).where(
            NotificacaoLogModel.status == "enviado",
            NotificacaoLogModel.template == "lembrete_devolucao",
        )
    )
    assert result_erro.scalar_one_or_none() is not None
    assert result_enviado.scalar_one_or_none() is not None


# ─── LEM-E2E-010 ──────────────────────────────────────────────────────────────

async def test_lem_e2e_010_segunda_execucao_reenvia_lembrete_mesma_data(
    db_session: AsyncSession,
) -> None:
    """LEM-E2E-010 — Segunda execução do job no mesmo banco reenvia (data_prevista = amanhã ainda)."""
    obra = await obra_factory(db_session, titulo="Obra LEM-010")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session, telefone="11999990300")
    await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=_amanha_utc(),
    )

    use_case = await _build_use_case(db_session)

    resultado1 = await use_case.execute()
    assert resultado1 == 1

    # Segunda execução: como data_prevista continua sendo amanhã, o use case
    # processa novamente (conforme nota do plano: sem deduplicação intra-dia no MVP)
    use_case2 = await _build_use_case(db_session)
    resultado2 = await use_case2.execute()
    assert resultado2 == 1
