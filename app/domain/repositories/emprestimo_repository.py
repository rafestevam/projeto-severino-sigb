from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.emprestimo import Emprestimo


class EmprestimoRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Emprestimo | None: ...

    @abstractmethod
    async def get_ativo_by_exemplar_qr(self, codigo_qr: str) -> Emprestimo | None: ...

    @abstractmethod
    async def list_by_leitor(self, leitor_id: UUID) -> list[Emprestimo]: ...

    @abstractmethod
    async def list_ativos(self) -> list[Emprestimo]: ...

    @abstractmethod
    async def list_ativos_vencidos(self) -> list[Emprestimo]: ...

    @abstractmethod
    async def list_filtered(
        self,
        leitor_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Emprestimo], int]: ...

    @abstractmethod
    async def save(self, emprestimo: Emprestimo) -> Emprestimo: ...

    @abstractmethod
    async def count_ativos_by_leitor(self, leitor_id: UUID) -> int: ...

    @abstractmethod
    async def list_com_vencimento_amanha(self) -> list[Emprestimo]: ...
