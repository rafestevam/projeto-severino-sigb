from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.adapters.api.schemas.obra import ObraIn
from app.domain.entities.obra import Obra
from app.domain.exceptions import DuplicateIsbnError
from app.domain.repositories.obra_repository import ObraRepository


class CadastrarObraUseCase:
    """Encapsulates the business logic for registering a new obra in the library."""

    def __init__(self, repo: ObraRepository) -> None:
        self._repo = repo

    async def execute(self, dados: ObraIn) -> Obra:
        """
        Create and persist a new Obra.

        Raises:
            DuplicateIsbnError: if an obra with the same ISBN already exists.
        """
        if dados.isbn is not None:
            existing = await self._repo.get_by_isbn(dados.isbn)
            if existing is not None:
                raise DuplicateIsbnError(dados.isbn)

        obra = Obra(
            id=uuid4(),
            isbn=dados.isbn,
            titulo=dados.titulo,
            autores=dados.autores,
            editora=dados.editora,
            ano=dados.ano,
            capa_url=dados.capa_url,
            categoria=dados.categoria,
            created_at=datetime.now(timezone.utc),
        )
        return await self._repo.save(obra)
