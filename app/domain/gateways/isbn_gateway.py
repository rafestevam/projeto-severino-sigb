from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.metadados_isbn import MetadadosIsbn


class IsbnGateway(ABC):
    """Abstract gateway for fetching book metadata from external ISBN sources."""

    @abstractmethod
    async def buscar(self, isbn: str) -> MetadadosIsbn | None:
        """
        Fetch metadata for the given ISBN.

        Returns:
            MetadadosIsbn with populated fields if found, or None if not found
            in any source.
        """
