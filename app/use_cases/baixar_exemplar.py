from __future__ import annotations

from uuid import UUID

from app.domain.entities.exemplar import Exemplar
from app.domain.exceptions import (
    ExemplarJaBaixadoError,
    ExemplarJaEmprestadoError,
    ExemplarNotFoundError,
)
from app.domain.repositories.emprestimo_repository import EmprestimoRepository
from app.domain.repositories.exemplar_repository import ExemplarRepository
from app.domain.repositories.inventario_log_repository import InventarioLogRepository


class BaixarExemplarUseCase:
    """US-020 — Dar baixa permanente em exemplar danificado ou extraviado.

    Valida que o exemplar existe e não está emprestado, atualiza seu estado
    para 'baixado', persiste o motivo e registra no log de auditoria.
    """

    def __init__(
        self,
        exemplar_repo: ExemplarRepository,
        emprestimo_repo: EmprestimoRepository,
        inventario_log_repo: InventarioLogRepository,
    ) -> None:
        self._exemplar_repo = exemplar_repo
        self._emprestimo_repo = emprestimo_repo
        self._inventario_log_repo = inventario_log_repo

    async def execute(
        self,
        exemplar_id: UUID,
        motivo: str,
        operador_keycloak_id: str,
    ) -> Exemplar:
        """Executa a baixa e retorna o exemplar atualizado.

        Raises:
            ExemplarNotFoundError: se o exemplar não existe.
            ExemplarJaBaixadoError: se o exemplar já foi baixado.
            ExemplarJaEmprestadoError: se o exemplar está atualmente emprestado.
        """
        exemplar = await self._exemplar_repo.get_by_id(exemplar_id)
        if exemplar is None:
            raise ExemplarNotFoundError(str(exemplar_id))

        if exemplar.estado == "baixado":
            raise ExemplarJaBaixadoError(str(exemplar_id))

        if exemplar.estado == "emprestado":
            raise ExemplarJaEmprestadoError(str(exemplar_id))

        exemplar_baixado = await self._exemplar_repo.update_baixa(exemplar_id, motivo)

        await self._inventario_log_repo.registrar(
            exemplar_id=exemplar_id,
            operador_keycloak_id=operador_keycloak_id,
            acao="baixado",
        )

        return exemplar_baixado  # type: ignore[return-value]
