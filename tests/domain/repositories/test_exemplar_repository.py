"""
Testes unitários para ExemplarRepository (ABC).

Estratégia: stub in-memory concreto que implementa todos os abstractmethods,
permitindo testar o contrato sem banco de dados.
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.domain.entities.exemplar import Exemplar
from app.domain.repositories.exemplar_repository import ExemplarRepository
from tests.domain.repositories.conftest import EXEMPLAR_ID, OBRA_ID, make_exemplar


# ---------------------------------------------------------------------------
# Stub in-memory
# ---------------------------------------------------------------------------

class InMemoryExemplarRepository(ExemplarRepository):
    def __init__(self) -> None:
        self._store: dict[UUID, Exemplar] = {}

    async def get_by_id(self, id: UUID) -> Exemplar | None:
        return self._store.get(id)

    async def get_by_codigo_qr(self, codigo_qr: str) -> Exemplar | None:
        return next((e for e in self._store.values() if e.codigo_qr == codigo_qr), None)

    async def list_by_obra(self, obra_id: UUID) -> list[Exemplar]:
        return [e for e in self._store.values() if e.obra_id == obra_id]

    async def save(self, exemplar: Exemplar) -> Exemplar:
        self._store[exemplar.id] = exemplar
        return exemplar

    async def update_estado(self, id: UUID, estado: str) -> Exemplar | None:
        exemplar = self._store.get(id)
        if exemplar is None:
            return None
        # dataclass com slots=True não permite atribuição direta; recria o objeto
        updated = Exemplar(
            id=exemplar.id,
            obra_id=exemplar.obra_id,
            codigo_qr=exemplar.codigo_qr,
            estado=estado,  # type: ignore[arg-type]
            localizacao_estante=exemplar.localizacao_estante,
            created_at=exemplar.created_at,
        )
        self._store[id] = updated
        return updated


# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------

@pytest.fixture
def repo() -> InMemoryExemplarRepository:
    return InMemoryExemplarRepository()


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

async def test_save_persiste_exemplar(repo: InMemoryExemplarRepository, exemplar: Exemplar) -> None:
    saved = await repo.save(exemplar)
    assert saved is exemplar


async def test_get_by_id_retorna_exemplar_salvo(repo: InMemoryExemplarRepository, exemplar: Exemplar) -> None:
    await repo.save(exemplar)
    result = await repo.get_by_id(exemplar.id)
    assert result == exemplar


async def test_get_by_id_retorna_none_quando_nao_existe(repo: InMemoryExemplarRepository) -> None:
    result = await repo.get_by_id(uuid4())
    assert result is None


async def test_get_by_codigo_qr_retorna_exemplar_correto(repo: InMemoryExemplarRepository, exemplar: Exemplar) -> None:
    await repo.save(exemplar)
    result = await repo.get_by_codigo_qr(exemplar.codigo_qr)
    assert result == exemplar


async def test_get_by_codigo_qr_retorna_none_quando_nao_existe(repo: InMemoryExemplarRepository) -> None:
    result = await repo.get_by_codigo_qr("QR-INEXISTENTE")
    assert result is None


async def test_list_by_obra_retorna_somente_exemplares_da_obra(repo: InMemoryExemplarRepository) -> None:
    outra_obra_id = uuid4()
    ex_obra1_a = make_exemplar(id=uuid4(), obra_id=OBRA_ID, codigo_qr="QR-A")
    ex_obra1_b = make_exemplar(id=uuid4(), obra_id=OBRA_ID, codigo_qr="QR-B")
    ex_outra   = make_exemplar(id=uuid4(), obra_id=outra_obra_id, codigo_qr="QR-C")

    await repo.save(ex_obra1_a)
    await repo.save(ex_obra1_b)
    await repo.save(ex_outra)

    result = await repo.list_by_obra(OBRA_ID)

    assert len(result) == 2
    assert ex_obra1_a in result
    assert ex_obra1_b in result
    assert ex_outra not in result


async def test_list_by_obra_retorna_lista_vazia_quando_nao_ha_exemplares(repo: InMemoryExemplarRepository) -> None:
    result = await repo.list_by_obra(uuid4())
    assert result == []


async def test_update_estado_altera_estado_do_exemplar(repo: InMemoryExemplarRepository, exemplar: Exemplar) -> None:
    await repo.save(exemplar)
    assert exemplar.estado == "disponivel"

    updated = await repo.update_estado(exemplar.id, "emprestado")

    assert updated is not None
    assert updated.estado == "emprestado"
    assert updated.id == exemplar.id


async def test_update_estado_retorna_none_para_id_inexistente(repo: InMemoryExemplarRepository) -> None:
    result = await repo.update_estado(uuid4(), "emprestado")
    assert result is None


async def test_abc_nao_pode_ser_instanciada_diretamente() -> None:
    with pytest.raises(TypeError):
        ExemplarRepository()  # type: ignore[abstract]
