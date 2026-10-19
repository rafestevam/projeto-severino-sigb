from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.leitor import Leitor


class LeitorRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Leitor | None: ...

    @abstractmethod
    async def get_by_cpf_hash(self, cpf_hash: str) -> Leitor | None: ...

    @abstractmethod
    async def list_ativos(self) -> list[Leitor]: ...

    @abstractmethod
    async def save(self, leitor: Leitor) -> Leitor: ...

    @abstractmethod
    async def ativar(self, id: UUID) -> Leitor | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Leitor | None:
        """Busca sem diferenciar maiúsculas/minúsculas.

        Retorna None se nenhum leitor ou mais de um usar o e-mail: um vínculo
        ambíguo não pode identificar quem está autenticado.
        """
