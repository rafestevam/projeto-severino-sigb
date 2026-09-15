from datetime import datetime
from uuid import uuid4

from app.domain.entities import Reserva


def test_reserva_instantiation_sets_all_attributes() -> None:
    reserva_id = uuid4()
    obra_id = uuid4()
    leitor_id = uuid4()
    created_at = datetime(2024, 1, 10, 14, 30)

    reserva = Reserva(
        id=reserva_id,
        obra_id=obra_id,
        leitor_id=leitor_id,
        status="aguardando",
        created_at=created_at,
    )

    assert reserva.id == reserva_id
    assert reserva.obra_id == obra_id
    assert reserva.leitor_id == leitor_id
    assert reserva.status == "aguardando"
    assert reserva.created_at == created_at
