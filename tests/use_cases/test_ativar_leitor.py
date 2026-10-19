"""
Testes unitários para AtivarLeitorUseCase (US-030).

Estratégia: AsyncMock para o LeitorRepository — sem banco de dados.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.exceptions import LeitorNaoEncontradoError
from app.use_cases.ativar_leitor import AtivarLeitorUseCase
from tests.domain.repositories.conftest import make_leitor


def _build_repo(leitor, ativado=None) -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=leitor)
    repo.ativar = AsyncMock(return_value=ativado)
    return repo


async def test_ativa_leitor_pendente() -> None:
    pendente = make_leitor(ativo=False)
    ativo = make_leitor(ativo=True)
    repo = _build_repo(pendente, ativado=ativo)

    resultado = await AtivarLeitorUseCase(repo).execute(pendente.id)

    assert resultado.ativo is True
    repo.ativar.assert_awaited_once_with(pendente.id)


async def test_e_idempotente_para_leitor_ja_ativo() -> None:
    ativo = make_leitor(ativo=True)
    repo = _build_repo(ativo)

    resultado = await AtivarLeitorUseCase(repo).execute(ativo.id)

    assert resultado is ativo
    repo.ativar.assert_not_awaited()


async def test_lanca_erro_para_leitor_inexistente() -> None:
    repo = _build_repo(None)

    with pytest.raises(LeitorNaoEncontradoError):
        await AtivarLeitorUseCase(repo).execute(uuid4())
    repo.ativar.assert_not_awaited()
