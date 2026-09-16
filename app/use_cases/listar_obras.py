from __future__ import annotations

from app.domain.entities.obra import Obra
from app.domain.repositories.obra_repository import ObraRepository


class ListarObrasUseCase:
    """Encapsulates the business logic for listing obras with optional filters and pagination."""

    def __init__(self, repo: ObraRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        titulo: str | None = None,
        autor: str | None = None,
        categoria: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Obra], int]:
        """
        Return a paginated and optionally filtered list of obras.

        Args:
            titulo: Optional partial match filter on the obra title.
            autor: Optional partial match filter on the obra authors.
            categoria: Optional partial match filter on the obra category.
            page: 1-based page number (default: 1).
            page_size: Number of items per page (default: 20).

        Returns:
            A tuple of (list of Obra, total count).
        """
        return await self._repo.list_filtered(
            titulo=titulo,
            autor=autor,
            categoria=categoria,
            page=page,
            page_size=page_size,
        )
