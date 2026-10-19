"""
Testes unitários para PreCadastrarLeitorUseCase (US-030).

Estratégia: AsyncMock para o LeitorRepository — sem banco de dados.
"""
from __future__ import annotations

from datetime import timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.entities.leitor import Leitor
from app.domain.exceptions import CpfInvalidoError, LeitorJaCadastradoError
from app.use_cases.pre_cadastrar_leitor import DadosPreCadastro, PreCadastrarLeitorUseCase
from tests.domain.repositories.conftest import make_leitor

_CPF = "529.982.247-25"


def _build_repo(existente: Leitor | None = None) -> MagicMock:
    repo = MagicMock()
    repo.get_by_cpf_hash = AsyncMock(return_value=existente)
    repo.save = AsyncMock(side_effect=lambda leitor: leitor)
    return repo


async def test_cria_leitor_pendente() -> None:
    repo = _build_repo()

    leitor = await PreCadastrarLeitorUseCase(repo).execute(
        DadosPreCadastro(nome="  Ana Lima ", cpf=_CPF, telefone="11999990000", email="Ana@Ex.com")
    )

    assert leitor.ativo is False
    assert leitor.nome == "Ana Lima"
    assert leitor.telefone == "11999990000"
    assert leitor.email == "ana@ex.com"
    assert leitor.created_at.tzinfo == timezone.utc
    repo.save.assert_awaited_once()


async def test_armazena_apenas_hash_do_cpf_normalizado() -> None:
    repo = _build_repo()

    leitor = await PreCadastrarLeitorUseCase(repo).execute(DadosPreCadastro(nome="Ana", cpf=_CPF))

    assert leitor.cpf_hash == Leitor.hash_cpf("52998224725")
    repo.get_by_cpf_hash.assert_awaited_once_with(Leitor.hash_cpf("52998224725"))


async def test_contatos_vazios_viram_none() -> None:
    repo = _build_repo()

    leitor = await PreCadastrarLeitorUseCase(repo).execute(
        DadosPreCadastro(nome="Ana", cpf=_CPF, telefone="  ", email="")
    )

    assert leitor.telefone is None
    assert leitor.email is None


async def test_cpf_invalido_lanca_erro_sem_consultar_repositorio() -> None:
    repo = _build_repo()

    with pytest.raises(CpfInvalidoError):
        await PreCadastrarLeitorUseCase(repo).execute(DadosPreCadastro(nome="Ana", cpf="111.111.111-11"))
    repo.get_by_cpf_hash.assert_not_awaited()
    repo.save.assert_not_awaited()


async def test_cpf_ja_cadastrado_lanca_erro_sem_salvar() -> None:
    repo = _build_repo(existente=make_leitor())

    with pytest.raises(LeitorJaCadastradoError):
        await PreCadastrarLeitorUseCase(repo).execute(DadosPreCadastro(nome="Ana", cpf=_CPF))
    repo.save.assert_not_awaited()
