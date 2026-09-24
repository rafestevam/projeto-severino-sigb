from __future__ import annotations

import logging
from app.domain.entities.emprestimo import Emprestimo
from app.domain.gateways.notificacao_gateway import NotificacaoGateway
from app.domain.repositories.emprestimo_repository import EmprestimoRepository

logger = logging.getLogger(__name__)

_TEMPLATE_EMPRESTIMO_ATRASADO = "emprestimo_atrasado"


class MarcarAtrasadosUseCase:
    """Encapsulates business rules for identifying and marking overdue loans.

    This use case is scheduled to run periodically (e.g. daily) to find loans
    with status 'ativo' whose 'data_prevista' is earlier than current time,
    transition their status to 'atrasado', save changes, and trigger notification.
    """

    def __init__(
        self,
        emprestimo_repo: EmprestimoRepository,
        notificacao_gateway: NotificacaoGateway,
    ) -> None:
        self._emprestimo_repo = emprestimo_repo
        self._notificacao_gateway = notificacao_gateway

    async def execute(self) -> int:
        """Mark all overdue active loans as 'atrasado' and enqueue reminder notifications.

        Returns:
            int: The number of loans marked as overdue.
        """
        vencidos = await self._emprestimo_repo.list_ativos_vencidos()
        marcados_count = 0

        for emprestimo in vencidos:
            emprestimo.status = "atrasado"
            await self._emprestimo_repo.save(emprestimo)
            marcados_count += 1
            await self._enviar_notificacao_lembrete(emprestimo)

        return marcados_count

    async def _enviar_notificacao_lembrete(self, emprestimo: Emprestimo) -> None:
        """Enqueues/sends reminder notification without interrupting flow on failures."""
        try:
            await self._notificacao_gateway.enviar(
                destino=str(emprestimo.leitor_id),
                template=_TEMPLATE_EMPRESTIMO_ATRASADO,
                params={
                    "emprestimo_id": str(emprestimo.id),
                    "exemplar_id": str(emprestimo.exemplar_id),
                    "data_prevista": emprestimo.data_prevista.isoformat(),
                },
            )
        except Exception:
            logger.exception(
                "Falha ao enviar notificação de atraso para leitor %s (empréstimo %s)",
                emprestimo.leitor_id,
                emprestimo.id,
            )
