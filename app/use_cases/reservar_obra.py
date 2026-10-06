from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.entities.reserva import Reserva
from app.domain.exceptions import (
    LeitorInativoError,
    ObraComExemplarDisponivelError,
    ReservaJaExisteError,
)
from app.domain.repositories.exemplar_repository import ExemplarRepository
from app.domain.repositories.leitor_repository import LeitorRepository
from app.domain.repositories.reserva_repository import ReservaRepository


class ReservarObraUseCase:
    """Encapsulates business rules for reserving a work when all copies are loaned out."""

    def __init__(
        self,
        exemplar_repo: ExemplarRepository,
        leitor_repo: LeitorRepository,
        reserva_repo: ReservaRepository,
    ) -> None:
        self._exemplar_repo = exemplar_repo
        self._leitor_repo = leitor_repo
        self._reserva_repo = reserva_repo

    async def execute(self, obra_id: UUID, leitor_id: UUID) -> tuple[Reserva, int]:
        """
        Reserve a work for a reader when all copies are loaned.

        Returns:
            A tuple of (reserva, posicao_fila) where posicao_fila is 1-based.

        Raises:
            LeitorInativoError: if the reader does not exist or is inactive.
            ObraComExemplarDisponivelError: if the work has at least one available copy.
            ReservaJaExisteError: if the reader already has an active reservation for the work.
        """
        leitor = await self._leitor_repo.get_by_id(leitor_id)
        if leitor is None or not leitor.ativo:
            raise LeitorInativoError(str(leitor_id))

        exemplares = await self._exemplar_repo.list_by_obra(obra_id)
        if any(e.estado == "disponivel" for e in exemplares):
            raise ObraComExemplarDisponivelError(str(obra_id))

        reserva_existente = await self._reserva_repo.get_ativa_by_leitor_e_obra(leitor_id, obra_id)
        if reserva_existente is not None:
            raise ReservaJaExisteError(str(obra_id), str(leitor_id))

        nova_reserva = Reserva(
            id=uuid4(),
            obra_id=obra_id,
            leitor_id=leitor_id,
            status="aguardando",
            created_at=datetime.now(timezone.utc),
        )
        nova_reserva = await self._reserva_repo.save(nova_reserva)

        todas_reservas = await self._reserva_repo.list_by_obra(obra_id)
        posicao = sum(1 for r in todas_reservas if r.status == "aguardando")

        return nova_reserva, posicao
