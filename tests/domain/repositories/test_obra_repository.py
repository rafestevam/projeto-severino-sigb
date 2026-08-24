"""
Testes unitários para ObraRepository (ABC).

Estratégia: implementar um stub in-memory concreto da ABC para
validar que o contrato é respeitado sem nenhuma dependência de banco.
Os métodos do stub são assíncronos para garantir compatibilidade com
o engine async que as implementações reais usarão.
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.domain.entities.obra import Obra
from app.domain.repositories.obra_repository import ObraRepository
from tests.domain.repositories.conftest import OBRA_ID, make_obra


# ---------------------------------------------------------------------------
# Stub in-memory — implementação concreta mínima da ABC
# ---------------------------------------------------------------------------

class InMemoryObraRepository(ObraRepository):
    def __init__(self) -> None:
        self._store: dict[UUID, Obra] = {}

    async def get_by_id(self, id: UUID) -> Obra | None:
        return self._store.get(id)

    async def get_by_isbn(self, isbn: str) -> Obra | None:
        return next((o for o in self._store.values() if o.isbn == isbn), None)

    async def list_all(self) -> list[Obra]:
        return list(self._store.values())

    async def save(self, obra: Obra) -> Obra:
        self._store[obra.id] = obra
        return obra

    async def delete(self, id: UUID) -> None:
        self._store.pop(id, None)


# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------

@pytest.fixture
def repo() -> InMemoryObraRepository:
    return InMemoryObraRepository()


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

async def test_save_persiste_obra(repo: InMemoryObraRepository, obra: Obra) -> None:
    saved = await repo.save(obra)
    assert saved is obra


async def test_get_by_id_retorna_obra_salva(repo: InMemoryObraRepository, obra: Obra) -> None:
    await repo.save(obra)
    result = await repo.get_by_id(obra.id)
    assert result == obra


async def test_get_by_id_retorna_none_quando_nao_existe(repo: InMemoryObraRepository) -> None:
    result = await repo.get_by_id(uuid4())
    assert result is None


async def test_get_by_isbn_retorna_obra_correta(repo: InMemoryObraRepository, obra: Obra) -> None:
    await repo.save(obra)
    result = await repo.get_by_isbn(obra.isbn)
    assert result == obra


async def test_get_by_isbn_retorna_none_quando_nao_existe(repo: InMemoryObraRepository) -> None:
    result = await repo.get_by_isbn("0000000000000")
    assert result is None


async def test_list_all_retorna_todas_as_obras(repo: InMemoryObraRepository) -> None:
    obra_a = make_obra(id=uuid4(), isbn="111", titulo="Obra A")
    obra_b = make_obra(id=uuid4(), isbn="222", titulo="Obra B")
    await repo.save(obra_a)
    await repo.save(obra_b)

    result = await repo.list_all()

    assert len(result) == 2
    assert obra_a in result
    assert obra_b in result


async def test_list_all_retorna_lista_vazia_quando_sem_dados(repo: InMemoryObraRepository) -> None:
    result = await repo.list_all()
    assert result == []


async def test_delete_remove_obra(repo: InMemoryObraRepository, obra: Obra) -> None:
    await repo.save(obra)
    await repo.delete(obra.id)
    result = await repo.get_by_id(obra.id)
    assert result is None


async def test_delete_de_id_inexistente_nao_levanta_excecao(repo: InMemoryObraRepository) -> None:
    # não deve lançar exceção
    await repo.delete(uuid4())


async def test_save_sobrescreve_obra_existente(repo: InMemoryObraRepository, obra: Obra) -> None:
    await repo.save(obra)
    obra_atualizada = make_obra(id=OBRA_ID, titulo="Titulo Atualizado")
    await repo.save(obra_atualizada)

    result = await repo.get_by_id(OBRA_ID)
    assert result is not None
    assert result.titulo == "Titulo Atualizado"
    assert len(await repo.list_all()) == 1


async def test_abc_nao_pode_ser_instanciada_diretamente() -> None:
    with pytest.raises(TypeError):
        ObraRepository()  # type: ignore[abstract]
