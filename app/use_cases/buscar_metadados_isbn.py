from __future__ import annotations

from app.adapters.api.schemas.isbn_metadata import IsbnMetadataOut
from app.domain.gateways.isbn_gateway import IsbnGateway


class BuscarMetadadosIsbnUseCase:
    """Encapsulates the business logic for fetching book metadata by ISBN."""

    def __init__(self, gateway: IsbnGateway) -> None:
        self._gateway = gateway

    async def execute(self, isbn: str) -> IsbnMetadataOut:
        """
        Fetch metadata for the given ISBN from external sources.

        Args:
            isbn: The ISBN to look up (ISBN-10 or ISBN-13).

        Returns:
            IsbnMetadataOut with populated fields when found, or an empty
            IsbnMetadataOut (all fields None) when no source returns data.
        """
        result = await self._gateway.buscar(isbn)
        return result if result is not None else IsbnMetadataOut()
