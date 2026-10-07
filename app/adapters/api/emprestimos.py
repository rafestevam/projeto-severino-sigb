from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import get_current_user, get_notificacao_gateway
from app.adapters.api.schemas.emprestimo import (
    CheckoutIn,
    DevolucaoQrIn,
    EmprestimoListOut,
    EmprestimoOut,
)
from app.adapters.repositories.sqlalchemy_configuracao_service import (
    ConfiguracaoServiceImpl,
)
from app.adapters.repositories.sqlalchemy_emprestimo_repository import (
    SQLAlchemyEmprestimoRepository,
)
from app.adapters.repositories.sqlalchemy_exemplar_repository import (
    SQLAlchemyExemplarRepository,
)
from app.adapters.repositories.sqlalchemy_leitor_repository import (
    SQLAlchemyLeitorRepository,
)
from app.adapters.repositories.sqlalchemy_obra_repository import (
    SQLAlchemyObraRepository,
)
from app.adapters.repositories.sqlalchemy_reserva_repository import (
    SQLAlchemyReservaRepository,
)
from app.domain.exceptions import (
    EmprestimoNaoEncontradoError,
    EmprestimoSemAtivoPorQrError,
    ExemplarNaoDisponivelError,
    ExemplarNotFoundError,
    LeitorInativoError,
    LimiteEmprestimosAtingidoError,
    LimiteRenovacoesAtingidoError,
)
from app.domain.gateways.notificacao_gateway import NotificacaoGateway
from app.infrastructure.database import get_db_session
from app.use_cases.listar_emprestimos import ListarEmprestimosUseCase
from app.use_cases.processar_devolucao import ProcessarDevolucaoUseCase
from app.use_cases.realizar_checkout import RealizarCheckoutUseCase
from app.use_cases.renovar_emprestimo import RenovarEmprestimoUseCase

emprestimos_router = APIRouter(prefix="/emprestimos", tags=["emprestimos"])


@emprestimos_router.post("", response_model=EmprestimoOut, status_code=status.HTTP_201_CREATED)
async def checkout(
    body: CheckoutIn,
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> EmprestimoOut:
    """US-011 — Realiza check-out de exemplar para leitor."""
    exemplar_repo = SQLAlchemyExemplarRepository(session)
    leitor_repo = SQLAlchemyLeitorRepository(session)
    emprestimo_repo = SQLAlchemyEmprestimoRepository(session)
    configuracao_service = ConfiguracaoServiceImpl(session)
    obra_repo = SQLAlchemyObraRepository(session)

    use_case = RealizarCheckoutUseCase(
        exemplar_repo=exemplar_repo,
        leitor_repo=leitor_repo,
        emprestimo_repo=emprestimo_repo,
        configuracao_service=configuracao_service,
        obra_repo=obra_repo,
    )

    try:
        emprestimo = await use_case.execute(
            exemplar_id=body.exemplar_id,
            leitor_id=body.leitor_id,
        )
    except ExemplarNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ExemplarNaoDisponivelError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except LeitorInativoError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LimiteEmprestimosAtingidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return EmprestimoOut.model_validate(emprestimo)


@emprestimos_router.post("/devolver-por-qr", response_model=EmprestimoOut)
async def devolver_por_qr(
    body: DevolucaoQrIn,
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
    notificacao_gateway: NotificacaoGateway = Depends(get_notificacao_gateway),
) -> EmprestimoOut:
    """US-012 — Realiza check-in de exemplar por bipagem de QR Code."""
    emprestimo_repo = SQLAlchemyEmprestimoRepository(session)
    exemplar_repo = SQLAlchemyExemplarRepository(session)
    reserva_repo = SQLAlchemyReservaRepository(session)
    leitor_repo = SQLAlchemyLeitorRepository(session)
    obra_repo = SQLAlchemyObraRepository(session)

    use_case = ProcessarDevolucaoUseCase(
        emprestimo_repo=emprestimo_repo,
        exemplar_repo=exemplar_repo,
        reserva_repo=reserva_repo,
        notificacao_gateway=notificacao_gateway,
        leitor_repo=leitor_repo,
        obra_repo=obra_repo,
    )

    try:
        emprestimo = await use_case.execute(body.codigo_qr)
    except EmprestimoSemAtivoPorQrError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return EmprestimoOut.model_validate(emprestimo)


@emprestimos_router.post("/{id}/devolver", response_model=EmprestimoOut)
async def devolver_por_id(
    id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
    notificacao_gateway: NotificacaoGateway = Depends(get_notificacao_gateway),
) -> EmprestimoOut:
    """US-012 — Realiza devolução de empréstimo por ID (fluxo alternativo)."""
    emprestimo_repo = SQLAlchemyEmprestimoRepository(session)
    exemplar_repo = SQLAlchemyExemplarRepository(session)
    reserva_repo = SQLAlchemyReservaRepository(session)
    leitor_repo = SQLAlchemyLeitorRepository(session)
    obra_repo = SQLAlchemyObraRepository(session)

    emprestimo = await emprestimo_repo.get_by_id(id)
    if emprestimo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Empréstimo não encontrado: {id}",
        )

    exemplar = await exemplar_repo.get_by_id(emprestimo.exemplar_id)
    if exemplar is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exemplar não encontrado: {emprestimo.exemplar_id}",
        )

    use_case = ProcessarDevolucaoUseCase(
        emprestimo_repo=emprestimo_repo,
        exemplar_repo=exemplar_repo,
        reserva_repo=reserva_repo,
        notificacao_gateway=notificacao_gateway,
        leitor_repo=leitor_repo,
        obra_repo=obra_repo,
    )

    try:
        emprestimo_devolvido = await use_case.execute(exemplar.codigo_qr)
    except EmprestimoSemAtivoPorQrError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return EmprestimoOut.model_validate(emprestimo_devolvido)


@emprestimos_router.post("/{id}/renovar", response_model=EmprestimoOut)
async def renovar_emprestimo(
    id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> EmprestimoOut:
    """US-013 — Renovar prazo de empréstimo."""
    emprestimo_repo = SQLAlchemyEmprestimoRepository(session)
    configuracao_service = ConfiguracaoServiceImpl(session)

    use_case = RenovarEmprestimoUseCase(
        emprestimo_repo=emprestimo_repo,
        configuracao_service=configuracao_service,
    )

    try:
        emprestimo = await use_case.execute(id)
    except EmprestimoNaoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except LimiteRenovacoesAtingidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return EmprestimoOut.model_validate(emprestimo)


@emprestimos_router.get("", response_model=EmprestimoListOut)
async def listar_emprestimos(
    leitor_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> EmprestimoListOut:
    """US-036 — Lista empréstimos com filtros e paginação."""
    emprestimo_repo = SQLAlchemyEmprestimoRepository(session)
    exemplar_repo = SQLAlchemyExemplarRepository(session)
    obra_repo = SQLAlchemyObraRepository(session)

    use_case = ListarEmprestimosUseCase(
        emprestimo_repo=emprestimo_repo,
        exemplar_repo=exemplar_repo,
        obra_repo=obra_repo,
    )

    items, total = await use_case.execute(
        leitor_id=leitor_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    return EmprestimoListOut(
        items=[EmprestimoOut.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
