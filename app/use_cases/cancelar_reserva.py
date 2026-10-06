from __future__ import annotations

from uuid import UUID

from app.domain.entities.reserva import Reserva
from app.domain.exceptions import ReservaNaoEncontradaError
from app.domain.repositories.reserva_repository import ReservaRepository


class CancelarReservaUseCase:
    """Encapsulates business rules for cancelling an existing reservation."""

    def __init__(self, reserva_repo: ReservaRepository) -> None:
        self._reserva_repo = reserva_repo

    async def execute(self, reserva_id: UUID) -> Reserva:
        """
        Cancel a reservation by updating its status to 'expirada'.

        Returns:
            The updated Reserva entity.

        Raises:
            ReservaNaoEncontradaError: if the reservation does not exist.
        """
        reserva = await self._reserva_repo.get_by_id(reserva_id)
        if reserva is None:
            raise ReservaNaoEncontradaError(str(reserva_id))

        reserva_atualizada = await self._reserva_repo.update_status(reserva_id, "expirada")
        # update_status returns None only if not found; we already confirmed existence above
        assert reserva_atualizada is not None
        return reserva_atualizada
