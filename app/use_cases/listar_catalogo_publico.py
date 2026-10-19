from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.disponibilidade_obra import DisponibilidadeObra
from app.domain.entities.obra import Obra
from app.domain.repositories.exemplar_repository import ExemplarRepository
from app.domain.repositories.obra_repository import ObraRepository


@dataclass(frozen=True, slots=True)
class ItemCatalogo:
    obra: Obra
    disponibilidade: DisponibilidadeObra


@dataclass(frozen=True, slots=True)
class PaginaCatalogo:
    itens: list[ItemCatalogo]
    total: int
    page: int
    page_size: int


class ListarCatalogoPublicoUseCase:
    """US-028 — Catálogo público (OPAC): busca única com disponibilidade agregada."""

    def __init__(self, obra_repo: ObraRepository, exemplar_repo: ExemplarRepository) -> None:
        self._obra_repo = obra_repo
        self._exemplar_repo = exemplar_repo

    async def execute(self, termo: str | None, page: int, page_size: int) -> PaginaCatalogo:
        obras, total = await self._obra_repo.buscar_catalogo_publico(termo, page, page_size)
        # Uma única consulta de disponibilidade para a página inteira (evita N+1).
        disponibilidades = await self._exemplar_repo.contar_disponibilidade(
            [obra.id for obra in obras]
        )
        itens = [
            ItemCatalogo(
                obra=obra,
                disponibilidade=disponibilidades.get(
                    obra.id, DisponibilidadeObra(obra.id, disponiveis=0, emprestados=0)
                ),
            )
            for obra in obras
        ]
        return PaginaCatalogo(itens=itens, total=total, page=page, page_size=page_size)
