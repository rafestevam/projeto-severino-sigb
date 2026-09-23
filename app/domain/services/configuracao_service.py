from __future__ import annotations

from abc import ABC, abstractmethod

CHAVE_DIAS_EMPRESTIMO = "dias_emprestimo"
CHAVE_MAX_RENOVACOES = "max_renovacoes"
CHAVE_MAX_EMPRESTIMOS_POR_LEITOR = "max_emprestimos_por_leitor"

DEFAULT_DIAS_EMPRESTIMO = 14
DEFAULT_MAX_RENOVACOES = 3
DEFAULT_MAX_EMPRESTIMOS_POR_LEITOR = 3


class ConfiguracaoService(ABC):
    """Abstract domain service for fetching circulation policies and system configurations."""

    @abstractmethod
    async def dias_emprestimo(self) -> int:
        """Returns the loan period in days."""
        ...

    @abstractmethod
    async def max_renovacoes(self) -> int:
        """Returns the maximum allowed renewals per loan."""
        ...

    @abstractmethod
    async def max_emprestimos_por_leitor(self) -> int:
        """Returns the maximum active loans allowed per reader."""
        ...
