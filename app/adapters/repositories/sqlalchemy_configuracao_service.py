from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.configuracao import ConfiguracaoModel
from app.domain.services.configuracao_service import (
    CHAVE_DIAS_EMPRESTIMO,
    CHAVE_MAX_EMPRESTIMOS_POR_LEITOR,
    CHAVE_MAX_RENOVACOES,
    ConfiguracaoService,
    DEFAULT_DIAS_EMPRESTIMO,
    DEFAULT_MAX_EMPRESTIMOS_POR_LEITOR,
    DEFAULT_MAX_RENOVACOES,
)


class ConfiguracaoServiceImpl(ConfiguracaoService):
    """SQLAlchemy implementation of ConfiguracaoService."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_valor(self, chave: str, default: int) -> int:
        result = await self._session.execute(
            select(ConfiguracaoModel.valor).where(ConfiguracaoModel.chave == chave)
        )
        valor = result.scalar_one_or_none()
        if valor is None:
            return default
        try:
            return int(valor)
        except ValueError:
            return default

    async def dias_emprestimo(self) -> int:
        return await self._get_valor(CHAVE_DIAS_EMPRESTIMO, DEFAULT_DIAS_EMPRESTIMO)

    async def max_renovacoes(self) -> int:
        return await self._get_valor(CHAVE_MAX_RENOVACOES, DEFAULT_MAX_RENOVACOES)

    async def max_emprestimos_por_leitor(self) -> int:
        return await self._get_valor(
            CHAVE_MAX_EMPRESTIMOS_POR_LEITOR, DEFAULT_MAX_EMPRESTIMOS_POR_LEITOR
        )