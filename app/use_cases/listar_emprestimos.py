from __future__ import annotations

# Design note (ST-04 / US-036):
# The enrichment of each Emprestimo with titulo_obra is performed here at the
# use-case layer using two sequential lookups per item (exemplar → obra).
# For the MVP with expected low volumes this N+1 pattern is acceptable.
# A future optimisation would push a JOIN into EmprestimoRepository and return
# the title alongside the loan row — document as technical debt.
from uuid import UUID

from app.domain.entities.emprestimo import Emprestimo, EmprestimoComTitulo
from app.domain.repositories.emprestimo_repository import EmprestimoRepository
from app.domain.repositories.exemplar_repository import ExemplarRepository
from app.domain.repositories.obra_repository import ObraRepository

_TITULO_DESCONHECIDO = "Obra desconhecida"


class ListarEmprestimosUseCase:
    """Return a paginated and filtered list of loans enriched with obra title."""

    def __init__(
        self,
        emprestimo_repo: EmprestimoRepository,
        exemplar_repo: ExemplarRepository,
        obra_repo: ObraRepository,
    ) -> None:
        self._emprestimo_repo = emprestimo_repo
        self._exemplar_repo = exemplar_repo
        self._obra_repo = obra_repo

    async def execute(
        self,
        leitor_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[EmprestimoComTitulo], int]:
        """
        List loans with optional filters, paginated, enriched with obra title.

        Args:
            leitor_id: Filter to loans belonging to a specific reader (optional).
            status: Filter by loan status — 'ativo', 'devolvido' or 'atrasado' (optional).
            page: 1-based page number (default: 1).
            page_size: Number of items per page (default: 20).

        Returns:
            A tuple of (list of EmprestimoComTitulo, total count).
        """
        emprestimos, total = await self._emprestimo_repo.list_filtered(
            leitor_id=leitor_id,
            status=status,
            page=page,
            page_size=page_size,
        )

        enriched: list[EmprestimoComTitulo] = []
        for emp in emprestimos:
            titulo = await self._resolve_titulo(emp)
            enriched.append(self._to_com_titulo(emp, titulo))

        return enriched, total

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _resolve_titulo(self, emp: Emprestimo) -> str:
        exemplar = await self._exemplar_repo.get_by_id(emp.exemplar_id)
        if exemplar is None:
            return _TITULO_DESCONHECIDO
        obra = await self._obra_repo.get_by_id(exemplar.obra_id)
        if obra is None:
            return _TITULO_DESCONHECIDO
        return obra.titulo

    @staticmethod
    def _to_com_titulo(emp: Emprestimo, titulo_obra: str) -> EmprestimoComTitulo:
        return EmprestimoComTitulo(
            id=emp.id,
            exemplar_id=emp.exemplar_id,
            leitor_id=emp.leitor_id,
            data_checkout=emp.data_checkout,
            data_prevista=emp.data_prevista,
            data_devolucao=emp.data_devolucao,
            renovacoes=emp.renovacoes,
            status=emp.status,
            titulo_obra=titulo_obra,
        )
