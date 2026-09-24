"""
Testes E2E — Sub-Tarefa 6: Marcar Empréstimos Atrasados — Job (US-014)
Casos: JOB-E2E-001 a JOB-E2E-007

Estratégia: invoca MarcarAtrasadosUseCase diretamente com banco real (db_session)
e emprestimo_factory para controle preciso de datas. Não depende de endpoint HTTP.

Cobre:
  - Empréstimo ativo + data_prevista ontem → marcado como "atrasado"
  - Empréstimo "devolvido" não é alterado
  - Empréstimo já "atrasado" não é reprocessado (idempotência)
  - Empréstimo dentro do prazo não é afetado
  - Múltiplos empréstimos vencidos processados em uma execução
  - execute() retorna contagem correta
  - Segunda execução retorna 0 (idempotência)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.emprestimo import EmprestimoModel
from app.adapters.repositories.sqlalchemy_emprestimo_repository import (
    SQLAlchemyEmprestimoRepository,
)
from app.infrastructure.notificacao_gateway_stub import NotificacaoGatewayStub
from app.use_cases.marcar_atrasados import MarcarAtrasadosUseCase
from tests.e2e.st_04_circulacao.conftest import (
    emprestimo_factory,
    exemplar_factory,
    leitor_factory,
    obra_factory,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _make_use_case(session: AsyncSession) -> MarcarAtrasadosUseCase:
    return MarcarAtrasadosUseCase(
        emprestimo_repo=SQLAlchemyEmprestimoRepository(session),
        notificacao_gateway=NotificacaoGatewayStub(),
    )


# ─── JOB-E2E-001 ─────────────────────────────────────────────────────────────

async def test_job_e2e_001_emprestimo_vencido_marcado_como_atrasado(
    db_session: AsyncSession,
) -> None:
    """JOB-E2E-001 — Empréstimo ativo com data_prevista ontem é marcado como 'atrasado'."""
    obra = await obra_factory(db_session, titulo="Obra JOB-001")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor = await leitor_factory(db_session)
    ontem = datetime.now(timezone.utc) - timedelta(days=1)
    emprestimo = await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=ontem,
        status="ativo",
    )

    use_case = _make_use_case(db_session)
    count = await use_case.execute()

    assert count >= 1

    # Verifica no banco
    model = await db_session.get(EmprestimoModel, emprestimo.id)
    assert model is not None
    assert model.status == "atrasado", f"Esperado 'atrasado', obtido '{model.status}'"


# ─── JOB-E2E-002 ─────────────────────────────────────────────────────────────

async def test_job_e2e_002_emprestimo_devolvido_nao_alterado(
    db_session: AsyncSession,
) -> None:
    """JOB-E2E-002 — Empréstimo com status='devolvido' não é alterado após execução do job."""
    obra = await obra_factory(db_session, titulo="Obra JOB-002")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session)
    ontem = datetime.now(timezone.utc) - timedelta(days=1)
    emprestimo = await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=ontem,
        status="devolvido",
    )

    use_case = _make_use_case(db_session)
    await use_case.execute()

    model = await db_session.get(EmprestimoModel, emprestimo.id)
    assert model is not None
    assert model.status == "devolvido", (
        f"Status não deveria ter mudado de 'devolvido', obtido '{model.status}'"
    )


# ─── JOB-E2E-003 ─────────────────────────────────────────────────────────────

async def test_job_e2e_003_emprestimo_ja_atrasado_nao_reprocessado(
    db_session: AsyncSession,
) -> None:
    """JOB-E2E-003 — Empréstimo já com status='atrasado' não é reprocessado (idempotência)."""
    obra = await obra_factory(db_session, titulo="Obra JOB-003")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session)
    ontem = datetime.now(timezone.utc) - timedelta(days=1)
    emprestimo = await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=ontem,
        status="atrasado",  # já está atrasado
    )

    use_case = _make_use_case(db_session)
    count = await use_case.execute()

    # Não deve ter contabilizado este como "novo" marcado
    assert count == 0

    model = await db_session.get(EmprestimoModel, emprestimo.id)
    assert model is not None
    assert model.status == "atrasado"


# ─── JOB-E2E-004 ─────────────────────────────────────────────────────────────

async def test_job_e2e_004_emprestimo_dentro_do_prazo_nao_afetado(
    db_session: AsyncSession,
) -> None:
    """JOB-E2E-004 — Empréstimo com data_prevista amanhã permanece 'ativo'."""
    obra = await obra_factory(db_session, titulo="Obra JOB-004")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor = await leitor_factory(db_session)
    amanha = datetime.now(timezone.utc) + timedelta(days=1)
    emprestimo = await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=amanha,
        status="ativo",
    )

    use_case = _make_use_case(db_session)
    await use_case.execute()

    model = await db_session.get(EmprestimoModel, emprestimo.id)
    assert model is not None
    assert model.status == "ativo", (
        f"Empréstimo dentro do prazo não deveria ter sido marcado, obtido '{model.status}'"
    )


# ─── JOB-E2E-005 ─────────────────────────────────────────────────────────────

async def test_job_e2e_005_multiplos_vencidos_marcados_em_uma_execucao(
    db_session: AsyncSession,
) -> None:
    """JOB-E2E-005 — Múltiplos empréstimos vencidos são marcados em uma única execução."""
    ontem = datetime.now(timezone.utc) - timedelta(days=1)
    ids_vencidos = []

    for i in range(3):
        obra = await obra_factory(db_session, titulo=f"Obra JOB-005-{i}")
        exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
        leitor = await leitor_factory(db_session)
        emp = await emprestimo_factory(
            db_session,
            exemplar_id=exemplar.id,
            leitor_id=leitor.id,
            data_prevista=ontem,
            status="ativo",
        )
        ids_vencidos.append(emp.id)

    use_case = _make_use_case(db_session)
    count = await use_case.execute()

    assert count >= 3, f"Esperado >= 3 marcados, obtido {count}"

    for emp_id in ids_vencidos:
        model = await db_session.get(EmprestimoModel, emp_id)
        assert model is not None
        assert model.status == "atrasado", (
            f"Empréstimo {emp_id} deveria ser 'atrasado', obtido '{model.status}'"
        )


# ─── JOB-E2E-006 ─────────────────────────────────────────────────────────────

async def test_job_e2e_006_execute_retorna_contagem_correta(
    db_session: AsyncSession,
) -> None:
    """JOB-E2E-006 — Use Case retorna o número correto de empréstimos marcados."""
    ontem = datetime.now(timezone.utc) - timedelta(days=1)

    # Cria exatamente 2 vencidos
    for i in range(2):
        obra = await obra_factory(db_session, titulo=f"Obra JOB-006-{i}")
        exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
        leitor = await leitor_factory(db_session)
        await emprestimo_factory(
            db_session,
            exemplar_id=exemplar.id,
            leitor_id=leitor.id,
            data_prevista=ontem,
            status="ativo",
        )

    use_case = _make_use_case(db_session)
    count = await use_case.execute()

    assert count == 2, f"Esperado 2 marcados, obtido {count}"


# ─── JOB-E2E-007 ─────────────────────────────────────────────────────────────

async def test_job_e2e_007_segunda_execucao_retorna_zero(
    db_session: AsyncSession,
) -> None:
    """JOB-E2E-007 — Segunda execução do job no mesmo banco retorna 0 (idempotência)."""
    obra = await obra_factory(db_session, titulo="Obra JOB-007")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    leitor = await leitor_factory(db_session)
    ontem = datetime.now(timezone.utc) - timedelta(days=1)
    await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=ontem,
        status="ativo",
    )

    use_case = _make_use_case(db_session)

    # Primeira execução: marca o empréstimo
    count1 = await use_case.execute()
    assert count1 >= 1

    # Segunda execução: não há mais empréstimos ativos vencidos para este conjunto
    count2 = await use_case.execute()
    assert count2 == 0, (
        f"Segunda execução deveria retornar 0, obtido {count2}"
    )
