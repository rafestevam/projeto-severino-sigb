from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MetadadosIsbn:
    """Metadados bibliográficos obtidos de fontes externas a partir de um ISBN."""

    titulo: str | None = None
    autores: list[str] | None = field(default=None)
    editora: str | None = None
    ano: int | None = None
    capa_url: str | None = None
    sinopse: str | None = None
