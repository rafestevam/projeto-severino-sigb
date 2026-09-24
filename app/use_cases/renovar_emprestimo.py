from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.domain.entities.emprestimo import Emprestimo
from app.domain.exceptions import (
    EmprestimoNaoEncontradoError,
    LimiteRenovacoesAtingidoError,
)
from app.domain.repositories.emprestimo_repository import EmprestimoRepository
from app.domain.services.configuracao_service import ConfiguracaoService


class RenovarEmprestimoUseCase:
    """Encapsulates all business rules for renewing an active loan."""

    def __init__(
        self,
        emprestimo_repo: EmprestimoRepository,
        configuracao_service: ConfiguracaoService,
    ) -> None:
        self._emprestimo_repo = emprestimo_repo
        self._configuracao_service = configuracao_service

    async def execute(self, emprestimo_id: UUID) -> Emprestimo:
        """
        Extend the loan period of an active loan by recalculating data_prevista
        from the current time and incrementing the renewal counter.

        Raises:
            EmprestimoNaoEncontradoError: if the loan does not exist.
            LimiteRenovacoesAtingidoError: if the loan has reached the renewal limit.
        """
        emprestimo = await self._emprestimo_repo.get_by_id(emprestimo_id)
        if emprestimo is None:
            raise EmprestimoNaoEncontradoError(str(emprestimo_id))

        max_renovacoes = await self._configuracao_service.max_renovacoes()
        if emprestimo.renovacoes >= max_renovacoes:
            raise LimiteRenovacoesAtingidoError(str(emprestimo_id), max_renovacoes)

        dias = await self._configuracao_service.dias_emprestimo()
        now = datetime.now(timezone.utc)

        emprestimo.data_prevista = now + timedelta(days=dias)
        emprestimo.renovacoes += 1

        return await self._emprestimo_repo.save(emprestimo)
