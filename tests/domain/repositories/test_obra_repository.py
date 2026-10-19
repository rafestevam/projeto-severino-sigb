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

    async def list_filtered(
        self,
        titulo: str | None = None,
        autor: str | None = None,
        categoria: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Obra], int]:
        results = list(self._store.values())
        if titulo:
            results = [o for o in results if titulo.lower() in o.titulo.lower()]
        if autor:
            results = [o for o in results if any(autor.lower() in a.lower() for a in o.autores)]
        if categoria:
            results = [o for o in results if categoria.lower() in o.categoria.lower()]
        total = len(results)
        offset = (page - 1) * page_size
        return results[offset : offset + page_size], total

    async def delete(self, id: UUID) -> None:
        self._store.pop(id, None)

    async def count_all(self) -> int:
        return len(self._store)

    async def list_top_emprestadas(self, limit: int = 10) -> list[Obra]:
        sorted_obras = sorted(
            self._store.values(),
            key=lambda o: getattr(o, "total_emprestimos", 0),
            reverse=True,
        )
        return sorted_obras[:limit]

    async def increment_total_emprestimos(self, obra_id: UUID) -> None:
        obra = self._store.get(obra_id)
        if obra is not None:
            updated = Obra(
                id=obra.id,
                isbn=obra.isbn,
                titulo=obra.titulo,
                autores=obra.autores,
                categoria=obra.categoria,
                ano_publicacao=obra.ano_publicacao,
                capa_url=obra.capa_url,
                total_emprestimos=obra.total_emprestimos + 1,
                created_at=obra.created_at,
            )
            self._store[obra_id] = updated

    async def buscar_catalogo_publico(
        self, termo: str | None, page: int, page_size: int
    ) -> tuple[list[Obra], int]:
        # O stub não conhece exemplares: o filtro de exemplares ativos (D3) é
        # coberto pelos testes de integração do repositório SQLAlchemy.
        results = sorted(self._store.values(), key=lambda o: o.titulo)
        if termo:
            t = termo.lower()
            results = [
                o for o in results
                if t in o.titulo.lower()
                or any(t in a.lower() for a in o.autores)
                or t in o.categoria.lower()
            ]
        offset = (page - 1) * page_size
        return results[offset : offset + page_size], len(results)

    async def get_posicao_ranking(self, obra_id: UUID) -> int | None:
        obra = self._store.get(obra_id)
        if obra is None or obra.total_emprestimos == 0:
            return None
        return 1 + sum(
            1 for o in self._store.values() if o.total_emprestimos > obra.total_emprestimos
        )


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


async def test_buscar_catalogo_publico_combina_campos_com_or(repo: InMemoryObraRepository) -> None:
    await repo.save(make_obra(id=uuid4(), titulo="Dom Casmurro", autores=["Machado"], categoria="Romance"))
    await repo.save(make_obra(id=uuid4(), titulo="Outro", autores=["Clarice"], categoria="Machado"))
    await repo.save(make_obra(id=uuid4(), titulo="Sem Relação", autores=["X"], categoria="Y"))

    obras, total = await repo.buscar_catalogo_publico("machado", page=1, page_size=10)

    assert total == 2
    assert {o.titulo for o in obras} == {"Dom Casmurro", "Outro"}


async def test_get_posicao_ranking_compartilha_posicao_em_empate(repo: InMemoryObraRepository) -> None:
    a = make_obra(id=uuid4(), titulo="A")
    a.total_emprestimos = 10
    b = make_obra(id=uuid4(), titulo="B")
    b.total_emprestimos = 10
    c = make_obra(id=uuid4(), titulo="C")
    c.total_emprestimos = 3
    for o in (a, b, c):
        await repo.save(o)

    assert await repo.get_posicao_ranking(a.id) == 1
    assert await repo.get_posicao_ranking(b.id) == 1
    assert await repo.get_posicao_ranking(c.id) == 3


async def test_get_posicao_ranking_none_para_obra_nunca_emprestada(
    repo: InMemoryObraRepository, obra: Obra
) -> None:
    await repo.save(obra)
    assert await repo.get_posicao_ranking(obra.id) is None
