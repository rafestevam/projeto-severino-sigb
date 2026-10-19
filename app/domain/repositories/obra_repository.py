from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.obra import Obra


class ObraRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Obra | None: ...

    @abstractmethod
    async def get_by_isbn(self, isbn: str) -> Obra | None: ...

    @abstractmethod
    async def list_all(self) -> list[Obra]: ...

    @abstractmethod
    async def list_filtered(
        self,
        titulo: str | None = None,
        autor: str | None = None,
        categoria: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Obra], int]: ...

    @abstractmethod
    async def save(self, obra: Obra) -> Obra: ...

    @abstractmethod
    async def delete(self, id: UUID) -> None: ...

    @abstractmethod
    async def count_all(self) -> int: ...

    @abstractmethod
    async def list_top_emprestadas(self, limit: int = 10) -> list[Obra]: ...

    @abstractmethod
    async def increment_total_emprestimos(self, obra_id: UUID) -> None: ...

    @abstractmethod
    async def buscar_catalogo_publico(
        self, termo: str | None, page: int, page_size: int
    ) -> tuple[list[Obra], int]:
        """Busca do OPAC: `termo` casa com título OU autor OU categoria.

        Só inclui obras com ao menos um exemplar não baixado, ordenadas por título.
        """

    @abstractmethod
    async def get_posicao_ranking(self, obra_id: UUID) -> int | None:
        """Posição da obra no "Preferidos da Galera" (1 = mais emprestada).

        Empates compartilham a posição. Retorna None se a obra nunca foi emprestada.
        """
