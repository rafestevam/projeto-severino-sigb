from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.entities.exemplar import Exemplar
from app.domain.exceptions import ObraNotFoundError
from app.domain.repositories.exemplar_repository import ExemplarRepository
from app.domain.repositories.obra_repository import ObraRepository


class AdicionarExemplaresUseCase:
    """Encapsulates the business logic for creating copies (exemplares) of an obra.

    Generates N exemplares with globally-unique QR codes in the format
    ``LIB-{ANO}-{SEQUENCIAL:05d}``.  The sequential counter is derived from
    a ``SELECT COUNT(*)`` over all existing exemplares — sufficient for the
    MVP; a proper PostgreSQL sequence should replace it if concurrent writes
    become a concern.
    """

    def __init__(
        self,
        obra_repo: ObraRepository,
        exemplar_repo: ExemplarRepository,
    ) -> None:
        self._obra_repo = obra_repo
        self._exemplar_repo = exemplar_repo

    async def execute(
        self,
        obra_id: UUID,
        quantidade: int,
        localizacao_estante: str,
    ) -> list[Exemplar]:
        """Create and persist *quantidade* exemplares for the given obra.

        Args:
            obra_id: UUID of the parent obra.
            quantidade: Number of exemplares to create (≥ 1).
            localizacao_estante: Shelf location string for all new exemplares.

        Returns:
            List of persisted Exemplar entities.

        Raises:
            ObraNotFoundError: if no obra with *obra_id* exists.
        """
        obra = await self._obra_repo.get_by_id(obra_id)
        if obra is None:
            raise ObraNotFoundError(str(obra_id))

        current_count = await self._exemplar_repo.count_all()
        ano = datetime.now(timezone.utc).year

        exemplares: list[Exemplar] = []
        for offset in range(quantidade):
            seq = current_count + offset + 1
            codigo_qr = f"LIB-{ano}-{seq:05d}"
            exemplar = Exemplar(
                id=uuid4(),
                obra_id=obra_id,
                codigo_qr=codigo_qr,
                estado="disponivel",
                localizacao_estante=localizacao_estante,
                created_at=datetime.now(timezone.utc),
            )
            saved = await self._exemplar_repo.save(exemplar)
            exemplares.append(saved)

        return exemplares
