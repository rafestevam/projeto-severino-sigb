from __future__ import annotations

import logging

from app.domain.gateways.notificacao_gateway import NotificacaoGateway
from app.domain.repositories.emprestimo_repository import EmprestimoRepository
from app.domain.repositories.exemplar_repository import ExemplarRepository
from app.domain.repositories.leitor_repository import LeitorRepository
from app.domain.repositories.obra_repository import ObraRepository

logger = logging.getLogger(__name__)

_TEMPLATE_LEMBRETE = "lembrete_devolucao"


class EnviarLembretesUseCase:
    """Sends D-1 return reminders to readers whose loans expire tomorrow."""

    def __init__(
        self,
        emprestimo_repo: EmprestimoRepository,
        leitor_repo: LeitorRepository,
        exemplar_repo: ExemplarRepository,
        obra_repo: ObraRepository,
        notificacao_gateway: NotificacaoGateway,
    ) -> None:
        self._emprestimo_repo = emprestimo_repo
        self._leitor_repo = leitor_repo
        self._exemplar_repo = exemplar_repo
        self._obra_repo = obra_repo
        self._notificacao_gateway = notificacao_gateway

    async def execute(self) -> int:
        """
        Find loans due tomorrow and send WhatsApp reminders.

        Returns:
            int: Number of reminder calls successfully dispatched.
        """
        emprestimos = await self._emprestimo_repo.list_com_vencimento_amanha()
        enviados = 0

        for emprestimo in emprestimos:
            leitor = await self._leitor_repo.get_by_id(emprestimo.leitor_id)
            if leitor is None or not leitor.telefone:
                continue

            titulo = await self._resolver_titulo(emprestimo.exemplar_id)

            try:
                await self._notificacao_gateway.enviar(
                    destino=leitor.telefone,
                    template=_TEMPLATE_LEMBRETE,
                    params={
                        "leitor_id": str(leitor.id),
                        "nome": leitor.nome,
                        "titulo": titulo,
                        "data_prevista": emprestimo.data_prevista.strftime("%d/%m/%Y"),
                    },
                )
                enviados += 1
            except Exception:
                logger.exception(
                    "Falha ao enviar lembrete para leitor %s (empréstimo %s)",
                    emprestimo.leitor_id,
                    emprestimo.id,
                )

        return enviados

    async def _resolver_titulo(self, exemplar_id) -> str:
        """Resolve obra title from exemplar_id, returning empty string on failure."""
        exemplar = await self._exemplar_repo.get_by_id(exemplar_id)
        if exemplar is None:
            return ""
        obra = await self._obra_repo.get_by_id(exemplar.obra_id)
        return obra.titulo if obra else ""
