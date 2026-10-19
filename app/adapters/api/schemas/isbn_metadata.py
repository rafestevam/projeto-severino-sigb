from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class IsbnMetadataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    titulo: str | None = None
    autores: list[str] | None = None
    editora: str | None = None
    ano: int | None = None
    capa_url: str | None = None
    sinopse: str | None = None
