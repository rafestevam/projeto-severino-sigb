"""
Testes unitários para ConfiguracaoService ABC e constantes em app/domain/services/.
"""
from __future__ import annotations

import pytest

from app.domain.services.configuracao_service import (
    CHAVE_DIAS_EMPRESTIMO,
    CHAVE_MAX_EMPRESTIMOS_POR_LEITOR,
    CHAVE_MAX_RENOVACOES,
    DEFAULT_DIAS_EMPRESTIMO,
    DEFAULT_MAX_EMPRESTIMOS_POR_LEITOR,
    DEFAULT_MAX_RENOVACOES,
    ConfiguracaoService,
)


def test_constantes_chaves():
    assert CHAVE_DIAS_EMPRESTIMO == "dias_emprestimo"
    assert CHAVE_MAX_RENOVACOES == "max_renovacoes"
    assert CHAVE_MAX_EMPRESTIMOS_POR_LEITOR == "max_emprestimos_por_leitor"


def test_constantes_padrao():
    assert DEFAULT_DIAS_EMPRESTIMO == 14
    assert DEFAULT_MAX_RENOVACOES == 3
    assert DEFAULT_MAX_EMPRESTIMOS_POR_LEITOR == 3


def test_configuracao_service_abc_nao_instanciavel():
    with pytest.raises(TypeError):
        ConfiguracaoService()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_configuracao_service_subclasse_valida():
    class DummyConfiguracaoService(ConfiguracaoService):
        async def dias_emprestimo(self) -> int:
            return 7

        async def max_renovacoes(self) -> int:
            return 2

        async def max_emprestimos_por_leitor(self) -> int:
            return 5

    service = DummyConfiguracaoService()
    assert await service.dias_emprestimo() == 7
    assert await service.max_renovacoes() == 2
    assert await service.max_emprestimos_por_leitor() == 5
