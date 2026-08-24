"""
Testes unitários para EmprestimoRepository (ABC).

Estratégia: stub in-memory concreto que implementa todos os abstractmethods,
permitindo testar o contrato sem banco de dados.
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.domain.entities.emprestimo import Emprestimo
from app.domain.repositories.emprestimo_repository import EmprestimoRepository
from tests.domain.repositories.conftest import LEITOR_ID, make_emprestimo


# ---------------------------------------------------------------------------
# Stub in-memory
# ---------------------------------------------------------------------------

class InMemoryEmprestimoRepository(EmprestimoRepository):
    def __init__(self) -> None:
        self._store: dict[UUID, Emprestimo] = {}

    async def get_by_id(self, id: UUID) -> Emprestimo | None:
        return self._store.get(id)

    async def list_by_leitor(self, leitor_id: UUID) -> list[Emprestimo]:
        return [e for e in self._store.values() if e.leitor_id == leitor_id]

    async def list_ativos(self) -> list[Emprestimo]:
        return [e for e in self._store.values() if e.status == "ativo"]

    async def save(self, emprestimo: Emprestimo) -> Emprestimo:
        self._store[emprestimo.id] = emprestimo
        return emprestimo

    async def count_ativos_by_leitor(self, leitor_id: UUID) -> int:
        return sum(
            1 for e in self._store.values()
            if e.leitor_id == leitor_id and e.status == "ativo"
        )


# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------

@pytest.fixture
def repo() -> InMemoryEmprestimoRepository:
    return InMemoryEmprestimoRepository()


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

async def test_save_persiste_emprestimo(
    repo: InMemoryEmprestimoRepository, emprestimo: Emprestimo
) -> None:
    saved = await repo.save(emprestimo)
    assert saved is emprestimo


async def test_get_by_id_retorna_emprestimo_salvo(
    repo: InMemoryEmprestimoRepository, emprestimo: Emprestimo
) -> None:
    await repo.save(emprestimo)
    result = await repo.get_by_id(emprestimo.id)
    assert result == emprestimo


async def test_get_by_id_retorna_none_quando_nao_existe(
    repo: InMemoryEmprestimoRepository,
) -> None:
    result = await repo.get_by_id(uuid4())
    assert result is None


async def test_list_by_leitor_retorna_somente_emprestimos_do_leitor(
    repo: InMemoryEmprestimoRepository,
) -> None:
    outro_leitor_id = uuid4()
    emp_leitor1_a = make_emprestimo(id=uuid4(), leitor_id=LEITOR_ID)
    emp_leitor1_b = make_emprestimo(id=uuid4(), leitor_id=LEITOR_ID)
    emp_outro     = make_emprestimo(id=uuid4(), leitor_id=outro_leitor_id)

    await repo.save(emp_leitor1_a)
    await repo.save(emp_leitor1_b)
    await repo.save(emp_outro)

    result = await repo.list_by_leitor(LEITOR_ID)

    assert len(result) == 2
    assert emp_leitor1_a in result
    assert emp_leitor1_b in result
    assert emp_outro not in result


async def test_list_by_leitor_retorna_lista_vazia_quando_sem_emprestimos(
    repo: InMemoryEmprestimoRepository,
) -> None:
    result = await repo.list_by_leitor(uuid4())
    assert result == []


async def test_list_ativos_retorna_somente_status_ativo(
    repo: InMemoryEmprestimoRepository,
) -> None:
    ativo1    = make_emprestimo(id=uuid4(), status="ativo")
    ativo2    = make_emprestimo(id=uuid4(), status="ativo")
    devolvido = make_emprestimo(id=uuid4(), status="devolvido")
    atrasado  = make_emprestimo(id=uuid4(), status="atrasado")

    for emp in (ativo1, ativo2, devolvido, atrasado):
        await repo.save(emp)

    result = await repo.list_ativos()

    assert len(result) == 2
    assert ativo1 in result
    assert ativo2 in result
    assert devolvido not in result
    assert atrasado not in result


async def test_list_ativos_retorna_lista_vazia_quando_nenhum_ativo(
    repo: InMemoryEmprestimoRepository,
) -> None:
    await repo.save(make_emprestimo(id=uuid4(), status="devolvido"))
    result = await repo.list_ativos()
    assert result == []


async def test_count_ativos_by_leitor_conta_apenas_ativos_do_leitor(
    repo: InMemoryEmprestimoRepository,
) -> None:
    outro_leitor_id = uuid4()

    await repo.save(make_emprestimo(id=uuid4(), leitor_id=LEITOR_ID, status="ativo"))
    await repo.save(make_emprestimo(id=uuid4(), leitor_id=LEITOR_ID, status="ativo"))
    await repo.save(make_emprestimo(id=uuid4(), leitor_id=LEITOR_ID, status="devolvido"))
    await repo.save(make_emprestimo(id=uuid4(), leitor_id=outro_leitor_id, status="ativo"))

    count = await repo.count_ativos_by_leitor(LEITOR_ID)

    assert count == 2


async def test_count_ativos_by_leitor_retorna_zero_sem_emprestimos_ativos(
    repo: InMemoryEmprestimoRepository,
) -> None:
    count = await repo.count_ativos_by_leitor(uuid4())
    assert count == 0


async def test_abc_nao_pode_ser_instanciada_diretamente() -> None:
    with pytest.raises(TypeError):
        EmprestimoRepository()  # type: ignore[abstract]
