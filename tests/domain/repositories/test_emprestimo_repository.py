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
        self.qr_to_exemplar_id: dict[str, UUID] = {}

    async def get_by_id(self, id: UUID) -> Emprestimo | None:
        return self._store.get(id)

    async def get_ativo_by_exemplar_qr(self, codigo_qr: str) -> Emprestimo | None:
        exemplar_id = self.qr_to_exemplar_id.get(codigo_qr)
        if not exemplar_id:
            return None
        for e in self._store.values():
            if e.exemplar_id == exemplar_id and e.status == "ativo":
                return e
        return None

    async def list_by_leitor(self, leitor_id: UUID) -> list[Emprestimo]:
        return [e for e in self._store.values() if e.leitor_id == leitor_id]

    async def list_ativos(self) -> list[Emprestimo]:
        return [e for e in self._store.values() if e.status == "ativo"]

    async def list_ativos_vencidos(self) -> list[Emprestimo]:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        return [
            e for e in self._store.values()
            if e.status == "ativo" and e.data_prevista < now
        ]

    async def list_filtered(
        self,
        leitor_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Emprestimo], int]:
        filtered = list(self._store.values())
        if leitor_id is not None:
            filtered = [e for e in filtered if e.leitor_id == leitor_id]
        if status is not None:
            filtered = [e for e in filtered if e.status == status]

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        return filtered[start:end], total

    async def save(self, emprestimo: Emprestimo) -> Emprestimo:
        self._store[emprestimo.id] = emprestimo
        return emprestimo

    async def count_ativos_by_leitor(self, leitor_id: UUID) -> int:
        return sum(
            1 for e in self._store.values()
            if e.leitor_id == leitor_id and e.status == "ativo"
        )

    async def list_com_vencimento_amanha(self) -> list[Emprestimo]:
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        amanha_inicio = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        amanha_fim = amanha_inicio + timedelta(days=1)
        return [
            e for e in self._store.values()
            if e.status == "ativo" and amanha_inicio <= e.data_prevista < amanha_fim
        ]


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


async def test_get_ativo_by_exemplar_qr(repo: InMemoryEmprestimoRepository) -> None:
    exemplar_id = uuid4()
    repo.qr_to_exemplar_id["QR123"] = exemplar_id
    emp_ativo = make_emprestimo(id=uuid4(), exemplar_id=exemplar_id, status="ativo")
    await repo.save(emp_ativo)

    res = await repo.get_ativo_by_exemplar_qr("QR123")
    assert res == emp_ativo

    res_none = await repo.get_ativo_by_exemplar_qr("QR_INEXISTENTE")
    assert res_none is None


async def test_list_filtered(repo: InMemoryEmprestimoRepository) -> None:
    leitor_a = uuid4()
    leitor_b = uuid4()
    emp1 = make_emprestimo(id=uuid4(), leitor_id=leitor_a, status="ativo")
    emp2 = make_emprestimo(id=uuid4(), leitor_id=leitor_a, status="devolvido")
    emp3 = make_emprestimo(id=uuid4(), leitor_id=leitor_b, status="ativo")

    for e in (emp1, emp2, emp3):
        await repo.save(e)

    # Sem filtros
    items, total = await repo.list_filtered(page=1, page_size=20)
    assert total == 3
    assert len(items) == 3

    # Filtro por leitor
    items_a, total_a = await repo.list_filtered(leitor_id=leitor_a)
    assert total_a == 2
    assert len(items_a) == 2

    # Filtro por status
    items_ativo, total_ativo = await repo.list_filtered(status="ativo")
    assert total_ativo == 2
    assert len(items_ativo) == 2

    # Filtro combinado
    items_comb, total_comb = await repo.list_filtered(leitor_id=leitor_a, status="ativo")
    assert total_comb == 1
    assert items_comb[0] == emp1

    # Paginação
    items_p1, total_p1 = await repo.list_filtered(page=1, page_size=2)
    assert total_p1 == 3
    assert len(items_p1) == 2
    items_p2, total_p2 = await repo.list_filtered(page=2, page_size=2)
    assert total_p2 == 3
    assert len(items_p2) == 1


async def test_list_ativos_vencidos(repo: InMemoryEmprestimoRepository) -> None:
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    vencido_ativo = make_emprestimo(
        id=uuid4(),
        status="ativo",
        data_prevista=now - timedelta(days=2),
    )
    no_prazo_ativo = make_emprestimo(
        id=uuid4(),
        status="ativo",
        data_prevista=now + timedelta(days=5),
    )
    vencido_devolvido = make_emprestimo(
        id=uuid4(),
        status="devolvido",
        data_prevista=now - timedelta(days=2),
    )
    vencido_atrasado = make_emprestimo(
        id=uuid4(),
        status="atrasado",
        data_prevista=now - timedelta(days=2),
    )

    for e in (vencido_ativo, no_prazo_ativo, vencido_devolvido, vencido_atrasado):
        await repo.save(e)

    result = await repo.list_ativos_vencidos()
    assert len(result) == 1
    assert result[0] == vencido_ativo


async def test_abc_nao_pode_ser_instanciada_diretamente() -> None:
    with pytest.raises(TypeError):
        EmprestimoRepository()  # type: ignore[abstract]
