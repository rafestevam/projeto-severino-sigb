"""Concrete implementation of IsbnGateway that queries external APIs in cascade.

Cascade order: Open Library → Google Books → CBL (only when CBL_API_KEY is set).
Each source is tried with a 5-second timeout. If a source fails or returns no data,
the next one is tried. Returns None when all sources fail.
"""
from __future__ import annotations

import os

import httpx

from app.adapters.api.schemas.isbn_metadata import IsbnMetadataOut
from app.domain.gateways.isbn_gateway import IsbnGateway

_OPEN_LIBRARY_URL = "https://openlibrary.org/api/books"
_GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
_CBL_URL = "https://isbn-search-br.search.windows.net/indexes/isbn-index/docs"

_TIMEOUT = 5.0


class IsbnGatewayImpl(IsbnGateway):
    """Fetches ISBN metadata from Open Library, Google Books and CBL in cascade."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    async def buscar(self, isbn: str) -> IsbnMetadataOut | None:
        """
        Query each source in order and return the first successful result.

        Returns:
            IsbnMetadataOut if any source returned metadata, None otherwise.
        """
        result = await self._buscar_open_library(isbn)
        if result is not None:
            return result

        result = await self._buscar_google_books(isbn)
        if result is not None:
            return result

        cbl_api_key = os.getenv("CBL_API_KEY")
        if cbl_api_key:
            result = await self._buscar_cbl(isbn, cbl_api_key)
            if result is not None:
                return result

        return None

    # ── private source queries ──────────────────────────────────────────────

    async def _buscar_open_library(self, isbn: str) -> IsbnMetadataOut | None:
        """Query Open Library Books API."""
        try:
            response = await self._client.get(
                _OPEN_LIBRARY_URL,
                params={"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"},
                timeout=_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return None

        book = data.get(f"ISBN:{isbn}")
        if not book:
            return None

        return self._map_open_library(book)

    async def _buscar_google_books(self, isbn: str) -> IsbnMetadataOut | None:
        """Query Google Books API."""
        try:
            response = await self._client.get(
                _GOOGLE_BOOKS_URL,
                params={"q": f"isbn:{isbn}"},
                timeout=_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return None

        items = data.get("items")
        if not items:
            return None

        volume_info = items[0].get("volumeInfo", {})
        return self._map_google_books(volume_info)

    async def _buscar_cbl(self, isbn: str, api_key: str) -> IsbnMetadataOut | None:
        """Query CBL (Câmara Brasileira do Livro) ISBN search API."""
        try:
            response = await self._client.get(
                _CBL_URL,
                params={
                    "search": isbn,
                    "searchFields": "FormattedKey,RowKey",
                    "api-version": "2016-09-01",
                },
                headers={"api-key": api_key},
                timeout=_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return None

        records = data.get("value")
        if not records:
            return None

        return self._map_cbl(records[0])

    # ── response mappers ────────────────────────────────────────────────────

    @staticmethod
    def _map_open_library(book: dict) -> IsbnMetadataOut:
        """Map Open Library book data to IsbnMetadataOut."""
        autores: list[str] | None = None
        raw_authors = book.get("authors")
        if raw_authors:
            autores = [a.get("name", "") for a in raw_authors if a.get("name")]

        editora: str | None = None
        publishers = book.get("publishers")
        if publishers:
            editora = publishers[0].get("name") if isinstance(publishers[0], dict) else str(publishers[0])

        ano: int | None = None
        publish_date = book.get("publish_date", "")
        if publish_date:
            # Attempt to extract a 4-digit year from strings like "2003" or "Jan 2003"
            for part in str(publish_date).split():
                if part.isdigit() and len(part) == 4:
                    ano = int(part)
                    break

        capa_url: str | None = None
        cover = book.get("cover")
        if cover:
            capa_url = cover.get("large") or cover.get("medium") or cover.get("small")

        return IsbnMetadataOut(
            titulo=book.get("title"),
            autores=autores or None,
            editora=editora,
            ano=ano,
            capa_url=capa_url,
        )

    @staticmethod
    def _map_google_books(volume_info: dict) -> IsbnMetadataOut:
        """Map Google Books volumeInfo to IsbnMetadataOut."""
        autores = volume_info.get("authors") or None

        ano: int | None = None
        published_date = volume_info.get("publishedDate", "")
        if published_date:
            year_part = str(published_date).split("-")[0]
            if year_part.isdigit() and len(year_part) == 4:
                ano = int(year_part)

        thumbnail: str | None = None
        image_links = volume_info.get("imageLinks", {})
        if image_links:
            thumbnail = image_links.get("thumbnail") or image_links.get("smallThumbnail")

        return IsbnMetadataOut(
            titulo=volume_info.get("title"),
            autores=autores,
            editora=volume_info.get("publisher"),
            ano=ano,
            capa_url=thumbnail,
        )

    @staticmethod
    def _map_cbl(record: dict) -> IsbnMetadataOut:
        """Map CBL record to IsbnMetadataOut."""
        autores: list[str] | None = None
        raw_authors = record.get("Authors") or record.get("authors")
        if isinstance(raw_authors, list) and raw_authors:
            autores = [str(a) for a in raw_authors]
        elif isinstance(raw_authors, str) and raw_authors:
            autores = [raw_authors]

        ano: int | None = None
        year_str = str(record.get("Ano") or record.get("ano") or "")
        if year_str.isdigit() and len(year_str) == 4:
            ano = int(year_str)

        return IsbnMetadataOut(
            titulo=record.get("Title") or record.get("title"),
            autores=autores,
            editora=record.get("Publisher") or record.get("publisher"),
            ano=ano,
            capa_url=None,
        )
