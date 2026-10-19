from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.disponibilidade_obra import DisponibilidadeObra
from app.domain.entities.obra import Obra
from app.domain.exceptions import ObraNotFoundError
from app.domain.repositories.exemplar_repository import ExemplarRepository
from app.domain.repositories.obra_repository import ObraRepository


@dataclass(frozen=True, slots=True)
class DetalheObraPublica:
    obra: Obra
    disponibilidade: DisponibilidadeObra
    posicao_ranking: int | None


class ObterObraPublicaUseCase:
    """US-029 — Detalhes públicos de uma obra, com disponibilidade e ranking."""

    def __init__(self, obra_repo: ObraRepository, exemplar_repo: ExemplarRepository) -> None:
        self._obra_repo = obra_repo
        self._exemplar_repo = exemplar_repo

    async def execute(self, obra_id: UUID) -> DetalheObraPublica:
        """
        Raises:
            ObraNotFoundError: se a obra não existe ou não tem exemplares ativos.
                Obras fora do catálogo público respondem como inexistentes para
                não vazar sua existência.
        """
        obra = await self._obra_repo.get_by_id(obra_id)
        if obra is None:
            raise ObraNotFoundError(str(obra_id))

        disponibilidades = await self._exemplar_repo.contar_disponibilidade([obra_id])
        disponibilidade = disponibilidades.get(obra_id)
        if disponibilidade is None or not disponibilidade.tem_exemplares_ativos:
            raise ObraNotFoundError(str(obra_id))

        posicao_ranking = await self._obra_repo.get_posicao_ranking(obra_id)
        return DetalheObraPublica(
            obra=obra,
            disponibilidade=disponibilidade,
            posicao_ranking=posicao_ranking,
        )
