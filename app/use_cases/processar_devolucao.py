from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.domain.entities.emprestimo import Emprestimo
from app.domain.exceptions import EmprestimoSemAtivoPorQrError
from app.domain.gateways.notificacao_gateway import NotificacaoGateway
from app.domain.repositories.emprestimo_repository import EmprestimoRepository
from app.domain.repositories.exemplar_repository import ExemplarRepository
from app.domain.repositories.reserva_repository import ReservaRepository

logger = logging.getLogger(__name__)

_TEMPLATE_RESERVA_DISPONIVEL = "reserva_disponivel"


class ProcessarDevolucaoUseCase:
    """Encapsulates all business rules for returning a copy via QR Code scan."""

    def __init__(
        self,
        emprestimo_repo: EmprestimoRepository,
        exemplar_repo: ExemplarRepository,
        reserva_repo: ReservaRepository,
        notificacao_gateway: NotificacaoGateway,
    ) -> None:
        self._emprestimo_repo = emprestimo_repo
        self._exemplar_repo = exemplar_repo
        self._reserva_repo = reserva_repo
        self._notificacao_gateway = notificacao_gateway

    async def execute(self, codigo_qr: str) -> Emprestimo:
        """
        Process the return of an exemplar identified by its QR code.

        Raises:
            EmprestimoSemAtivoPorQrError: if no active loan exists for the given QR code.
        """
        emprestimo = await self._emprestimo_repo.get_ativo_by_exemplar_qr(codigo_qr)
        if emprestimo is None:
            raise EmprestimoSemAtivoPorQrError(codigo_qr)

        now = datetime.now(timezone.utc)
        emprestimo.data_devolucao = now
        emprestimo.status = "devolvido"

        await self._exemplar_repo.update_estado(emprestimo.exemplar_id, "disponivel")
        emprestimo = await self._emprestimo_repo.save(emprestimo)

        await self._verificar_e_notificar_reserva(emprestimo)

        return emprestimo

    # ── private helpers ──────────────────────────────────────────────────────

    async def _verificar_e_notificar_reserva(self, emprestimo: Emprestimo) -> None:
        """Check for a waiting reservation on the returned copy's work and notify."""
        exemplar = await self._exemplar_repo.get_by_id(emprestimo.exemplar_id)
        if exemplar is None:
            return

        reserva = await self._reserva_repo.get_proxima_aguardando(exemplar.obra_id)
        if reserva is None:
            return

        await self._reserva_repo.update_status(reserva.id, "disponivel")

        asyncio.create_task(
            self._enviar_notificacao(
                destino=str(reserva.leitor_id),
                params={
                    "reserva_id": str(reserva.id),
                    "obra_id": str(exemplar.obra_id),
                },
            )
        )

    async def _enviar_notificacao(self, destino: str, params: dict) -> None:
        """Fire-and-forget wrapper; logs errors without propagating them."""
        try:
            await self._notificacao_gateway.enviar(
                destino=destino,
                template=_TEMPLATE_RESERVA_DISPONIVEL,
                params=params,
            )
        except Exception:
            logger.exception("Falha ao enviar notificação para %s", destino)
