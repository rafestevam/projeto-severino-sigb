"""
Testes unitários para LeitorRepository (ABC).

Estratégia: stub in-memory concreto que implementa todos os abstractmethods,
permitindo testar o contrato sem banco de dados.
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.domain.entities.leitor import Leitor
from app.domain.repositories.leitor_repository import LeitorRepository
from tests.domain.repositories.conftest import make_leitor


# ---------------------------------------------------------------------------
# Stub in-memory
# ---------------------------------------------------------------------------

class InMemoryLeitorRepository(LeitorRepository):
    def __init__(self) -> None:
        self._store: dict[UUID, Leitor] = {}

    async def get_by_id(self, id: UUID) -> Leitor | None:
        return self._store.get(id)

    async def get_by_cpf_hash(self, cpf_hash: str) -> Leitor | None:
        return next((l for l in self._store.values() if l.cpf_hash == cpf_hash), None)

    async def list_ativos(self) -> list[Leitor]:
        return [l for l in self._store.values() if l.ativo]

    async def save(self, leitor: Leitor) -> Leitor:
        self._store[leitor.id] = leitor
        return leitor


# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------

@pytest.fixture
def repo() -> InMemoryLeitorRepository:
    return InMemoryLeitorRepository()


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

async def test_save_persiste_leitor(repo: InMemoryLeitorRepository, leitor: Leitor) -> None:
    saved = await repo.save(leitor)
    assert saved is leitor


async def test_get_by_id_retorna_leitor_salvo(repo: InMemoryLeitorRepository, leitor: Leitor) -> None:
    await repo.save(leitor)
    result = await repo.get_by_id(leitor.id)
    assert result == leitor


async def test_get_by_id_retorna_none_quando_nao_existe(repo: InMemoryLeitorRepository) -> None:
    result = await repo.get_by_id(uuid4())
    assert result is None


async def test_get_by_cpf_hash_retorna_leitor_correto(repo: InMemoryLeitorRepository, leitor: Leitor) -> None:
    await repo.save(leitor)
    result = await repo.get_by_cpf_hash(leitor.cpf_hash)
    assert result == leitor


async def test_get_by_cpf_hash_retorna_none_para_hash_inexistente(repo: InMemoryLeitorRepository) -> None:
    result = await repo.get_by_cpf_hash("hash_que_nao_existe")
    assert result is None


async def test_get_by_cpf_hash_usa_hash_calculado_pela_entidade(repo: InMemoryLeitorRepository) -> None:
    """Garante que o repositório recebe e filtra pelo hash; a conversão CPF→hash
    é responsabilidade do chamador (entidade Leitor.hash_cpf)."""
    cpf = "98765432100"
    expected_hash = Leitor.hash_cpf(cpf)
    leitor = make_leitor(id=uuid4(), cpf_hash=expected_hash)

    await repo.save(leitor)
    result = await repo.get_by_cpf_hash(expected_hash)

    assert result == leitor


async def test_list_ativos_retorna_somente_leitores_ativos(repo: InMemoryLeitorRepository) -> None:
    ativo1  = make_leitor(id=uuid4(), nome="Ativo 1",   ativo=True)
    ativo2  = make_leitor(id=uuid4(), nome="Ativo 2",   ativo=True)
    inativo = make_leitor(id=uuid4(), nome="Inativo 1", ativo=False)

    await repo.save(ativo1)
    await repo.save(ativo2)
    await repo.save(inativo)

    result = await repo.list_ativos()

    assert len(result) == 2
    assert ativo1 in result
    assert ativo2 in result
    assert inativo not in result


async def test_list_ativos_retorna_lista_vazia_quando_nenhum_ativo(repo: InMemoryLeitorRepository) -> None:
    await repo.save(make_leitor(id=uuid4(), ativo=False))
    result = await repo.list_ativos()
    assert result == []


async def test_abc_nao_pode_ser_instanciada_diretamente() -> None:
    with pytest.raises(TypeError):
        LeitorRepository()  # type: ignore[abstract]
