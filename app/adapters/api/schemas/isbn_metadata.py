from __future__ import annotations

from pydantic import BaseModel


class IsbnMetadataOut(BaseModel):
    titulo: str | None = None
    autores: list[str] | None = None
    editora: str | None = None
    ano: int | None = None
    capa_url: str | None = None
