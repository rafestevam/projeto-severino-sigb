from __future__ import annotations

from abc import ABC, abstractmethod

from app.adapters.api.schemas.isbn_metadata import IsbnMetadataOut


class IsbnGateway(ABC):
    """Abstract gateway for fetching book metadata from external ISBN sources."""

    @abstractmethod
    async def buscar(self, isbn: str) -> IsbnMetadataOut | None:
        """
        Fetch metadata for the given ISBN.

        Returns:
            IsbnMetadataOut with populated fields if found, or None if not found
            in any source.
        """
