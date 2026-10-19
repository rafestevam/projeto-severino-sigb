from __future__ import annotations

from uuid import UUID

from app.domain.entities.leitor import Leitor
from app.domain.exceptions import LeitorNaoEncontradoError
from app.domain.repositories.leitor_repository import LeitorRepository


class AtivarLeitorUseCase:
    """US-030 — Operador ativa no balcão um leitor pré-cadastrado (pendente)."""

    def __init__(self, leitor_repo: LeitorRepository) -> None:
        self._leitor_repo = leitor_repo

    async def execute(self, leitor_id: UUID) -> Leitor:
        """
        Idempotente: um leitor já ativo é devolvido sem nova escrita.

        Raises:
            LeitorNaoEncontradoError: se o leitor não existe.
        """
        leitor = await self._leitor_repo.get_by_id(leitor_id)
        if leitor is None:
            raise LeitorNaoEncontradoError(str(leitor_id))
        if leitor.ativo:
            return leitor

        ativado = await self._leitor_repo.ativar(leitor_id)
        if ativado is None:
            raise LeitorNaoEncontradoError(str(leitor_id))
        return ativado
