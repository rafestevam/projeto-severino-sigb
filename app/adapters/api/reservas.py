from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import get_current_user
from app.adapters.api.schemas.reserva import ReservaIn, ReservaOut
from app.adapters.repositories.sqlalchemy_exemplar_repository import (
    SQLAlchemyExemplarRepository,
)
from app.adapters.repositories.sqlalchemy_leitor_repository import (
    SQLAlchemyLeitorRepository,
)
from app.adapters.repositories.sqlalchemy_reserva_repository import (
    SQLAlchemyReservaRepository,
)
from app.domain.exceptions import (
    LeitorInativoError,
    ObraComExemplarDisponivelError,
    ReservaJaExisteError,
    ReservaNaoEncontradaError,
)
from app.infrastructure.database import get_db_session
from app.use_cases.cancelar_reserva import CancelarReservaUseCase
from app.use_cases.reservar_obra import ReservarObraUseCase

reservas_router = APIRouter(prefix="/reservas", tags=["reservas"])


@reservas_router.post("", response_model=ReservaOut, status_code=status.HTTP_201_CREATED)
async def criar_reserva(
    body: ReservaIn,
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> ReservaOut:
    """US-015 — Reserva uma obra quando todos os exemplares estão emprestados."""
    exemplar_repo = SQLAlchemyExemplarRepository(session)
    leitor_repo = SQLAlchemyLeitorRepository(session)
    reserva_repo = SQLAlchemyReservaRepository(session)

    use_case = ReservarObraUseCase(
        exemplar_repo=exemplar_repo,
        leitor_repo=leitor_repo,
        reserva_repo=reserva_repo,
    )

    try:
        reserva, posicao = await use_case.execute(body.obra_id, body.leitor_id)
    except LeitorInativoError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ObraComExemplarDisponivelError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ReservaJaExisteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    out = ReservaOut.model_validate(reserva)
    out.posicao_fila = posicao
    return out


@reservas_router.delete("/{id}", response_model=ReservaOut)
async def cancelar_reserva(
    id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> ReservaOut:
    """US-015 — Cancela (expira) uma reserva existente."""
    reserva_repo = SQLAlchemyReservaRepository(session)

    use_case = CancelarReservaUseCase(reserva_repo=reserva_repo)

    try:
        reserva = await use_case.execute(id)
    except ReservaNaoEncontradaError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ReservaOut.model_validate(reserva)
