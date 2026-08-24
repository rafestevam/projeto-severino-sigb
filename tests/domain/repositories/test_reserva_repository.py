"""
Testes unitários para ReservaRepository (ABC).

Estratégia: stub in-memory concreto que implementa todos os abstractmethods,
permitindo testar o contrato sem banco de dados.
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.domain.entities.reserva import Reserva
from app.domain.repositories.reserva_repository import ReservaRepository
from tests.domain.repositories.conftest import OBRA_ID, make_reserva


# ---------------------------------------------------------------------------
# Stub in-memory
# ---------------------------------------------------------------------------

class InMemoryReservaRepository(ReservaRepository):
    def __init__(self) -> None:
        self._store: dict[UUID, Reserva] = {}

    async def get_by_id(self, id: UUID) -> Reserva | None:
        return self._store.get(id)

    async def list_by_obra(self, obra_id: UUID) -> list[Reserva]:
        return [r for r in self._store.values() if r.obra_id == obra_id]

    async def get_proxima_aguardando(self, obra_id: UUID) -> Reserva | None:
        """Retorna a reserva mais antiga com status 'aguardando' para a obra."""
        candidatas = [
            r for r in self._store.values()
            if r.obra_id == obra_id and r.status == "aguardando"
        ]
        return min(candidatas, key=lambda r: r.created_at, default=None)

    async def save(self, reserva: Reserva) -> Reserva:
        self._store[reserva.id] = reserva
        return reserva

    async def update_status(self, id: UUID, status: str) -> Reserva | None:
        reserva = self._store.get(id)
        if reserva is None:
            return None
        # dataclass com slots=True não permite atribuição direta; recria o objeto
        updated = Reserva(
            id=reserva.id,
            obra_id=reserva.obra_id,
            leitor_id=reserva.leitor_id,
            status=status,  # type: ignore[arg-type]
            created_at=reserva.created_at,
        )
        self._store[id] = updated
        return updated


# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------

@pytest.fixture
def repo() -> InMemoryReservaRepository:
    return InMemoryReservaRepository()


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

async def test_save_persiste_reserva(repo: InMemoryReservaRepository, reserva: Reserva) -> None:
    saved = await repo.save(reserva)
    assert saved is reserva


async def test_get_by_id_retorna_reserva_salva(repo: InMemoryReservaRepository, reserva: Reserva) -> None:
    await repo.save(reserva)
    result = await repo.get_by_id(reserva.id)
    assert result == reserva


async def test_get_by_id_retorna_none_quando_nao_existe(repo: InMemoryReservaRepository) -> None:
    result = await repo.get_by_id(uuid4())
    assert result is None


async def test_list_by_obra_retorna_somente_reservas_da_obra(
    repo: InMemoryReservaRepository,
) -> None:
    outra_obra_id = uuid4()
    res_obra1_a = make_reserva(id=uuid4(), obra_id=OBRA_ID)
    res_obra1_b = make_reserva(id=uuid4(), obra_id=OBRA_ID)
    res_outra   = make_reserva(id=uuid4(), obra_id=outra_obra_id)

    await repo.save(res_obra1_a)
    await repo.save(res_obra1_b)
    await repo.save(res_outra)

    result = await repo.list_by_obra(OBRA_ID)

    assert len(result) == 2
    assert res_obra1_a in result
    assert res_obra1_b in result
    assert res_outra not in result


async def test_list_by_obra_retorna_lista_vazia_quando_sem_reservas(
    repo: InMemoryReservaRepository,
) -> None:
    result = await repo.list_by_obra(uuid4())
    assert result == []


async def test_get_proxima_aguardando_retorna_reserva_mais_antiga(
    repo: InMemoryReservaRepository,
) -> None:
    from datetime import datetime

    mais_antiga = make_reserva(id=uuid4(), obra_id=OBRA_ID, status="aguardando",
                               created_at=datetime(2024, 1, 1))
    mais_recente = make_reserva(id=uuid4(), obra_id=OBRA_ID, status="aguardando",
                                created_at=datetime(2024, 6, 1))

    await repo.save(mais_recente)
    await repo.save(mais_antiga)

    result = await repo.get_proxima_aguardando(OBRA_ID)

    assert result is not None
    assert result.id == mais_antiga.id


async def test_get_proxima_aguardando_ignora_outros_status(
    repo: InMemoryReservaRepository,
) -> None:
    await repo.save(make_reserva(id=uuid4(), obra_id=OBRA_ID, status="disponivel"))
    await repo.save(make_reserva(id=uuid4(), obra_id=OBRA_ID, status="expirada"))
    await repo.save(make_reserva(id=uuid4(), obra_id=OBRA_ID, status="atendida"))

    result = await repo.get_proxima_aguardando(OBRA_ID)

    assert result is None


async def test_get_proxima_aguardando_retorna_none_quando_sem_reservas(
    repo: InMemoryReservaRepository,
) -> None:
    result = await repo.get_proxima_aguardando(uuid4())
    assert result is None


async def test_update_status_altera_status_da_reserva(
    repo: InMemoryReservaRepository, reserva: Reserva
) -> None:
    await repo.save(reserva)
    assert reserva.status == "aguardando"

    updated = await repo.update_status(reserva.id, "disponivel")

    assert updated is not None
    assert updated.status == "disponivel"
    assert updated.id == reserva.id


async def test_update_status_retorna_none_para_id_inexistente(
    repo: InMemoryReservaRepository,
) -> None:
    result = await repo.update_status(uuid4(), "disponivel")
    assert result is None


async def test_update_status_persiste_novo_status(
    repo: InMemoryReservaRepository, reserva: Reserva
) -> None:
    await repo.save(reserva)
    await repo.update_status(reserva.id, "atendida")

    result = await repo.get_by_id(reserva.id)
    assert result is not None
    assert result.status == "atendida"


async def test_abc_nao_pode_ser_instanciada_diretamente() -> None:
    with pytest.raises(TypeError):
        ReservaRepository()  # type: ignore[abstract]
