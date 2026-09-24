from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.domain.entities.emprestimo import Emprestimo
from app.domain.exceptions import (
    ExemplarNaoDisponivelError,
    ExemplarNotFoundError,
    LeitorInativoError,
    LimiteEmprestimosAtingidoError,
)
from app.domain.repositories.emprestimo_repository import EmprestimoRepository
from app.domain.repositories.exemplar_repository import ExemplarRepository
from app.domain.repositories.leitor_repository import LeitorRepository
from app.domain.services.configuracao_service import ConfiguracaoService


class RealizarCheckoutUseCase:
    """Encapsulates all business rules for checking out a copy to a reader."""

    def __init__(
        self,
        exemplar_repo: ExemplarRepository,
        leitor_repo: LeitorRepository,
        emprestimo_repo: EmprestimoRepository,
        configuracao_service: ConfiguracaoService,
    ) -> None:
        self._exemplar_repo = exemplar_repo
        self._leitor_repo = leitor_repo
        self._emprestimo_repo = emprestimo_repo
        self._configuracao_service = configuracao_service

    async def execute(self, exemplar_id: UUID, leitor_id: UUID) -> Emprestimo:
        """
        Perform a check-out of an exemplar to a reader.

        Raises:
            ExemplarNotFoundError: if the exemplar does not exist.
            ExemplarNaoDisponivelError: if the exemplar is not in 'disponivel' state.
            LeitorInativoError: if the reader is not active.
            LimiteEmprestimosAtingidoError: if the reader has reached the active loan limit.
        """
        exemplar = await self._exemplar_repo.get_by_id(exemplar_id)
        if exemplar is None:
            raise ExemplarNotFoundError(str(exemplar_id))

        if exemplar.estado != "disponivel":
            raise ExemplarNaoDisponivelError(str(exemplar_id), exemplar.estado)

        leitor = await self._leitor_repo.get_by_id(leitor_id)
        if leitor is None or not leitor.ativo:
            raise LeitorInativoError(str(leitor_id))

        max_emprestimos = await self._configuracao_service.max_emprestimos_por_leitor()
        ativos = await self._emprestimo_repo.count_ativos_by_leitor(leitor_id)
        if ativos >= max_emprestimos:
            raise LimiteEmprestimosAtingidoError(str(leitor_id), max_emprestimos)

        dias = await self._configuracao_service.dias_emprestimo()
        now = datetime.now(timezone.utc)

        emprestimo = Emprestimo(
            id=uuid4(),
            exemplar_id=exemplar_id,
            leitor_id=leitor_id,
            data_checkout=now,
            data_prevista=now + timedelta(days=dias),
            data_devolucao=None,
            renovacoes=0,
            status="ativo",
        )

        await self._exemplar_repo.update_estado(exemplar_id, "emprestado")
        return await self._emprestimo_repo.save(emprestimo)
