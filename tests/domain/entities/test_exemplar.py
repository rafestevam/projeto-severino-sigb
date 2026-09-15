from datetime import datetime
from uuid import uuid4

from app.domain.entities import Exemplar


def test_exemplar_accepts_expected_estado_literals() -> None:
    obra_id = uuid4()
    created_at = datetime(2024, 1, 10, 14, 30)

    exemplar_disponivel = Exemplar(
        id=uuid4(),
        obra_id=obra_id,
        codigo_qr="QR-001",
        estado="disponivel",
        localizacao_estante="A1",
        created_at=created_at,
    )
    exemplar_emprestado = Exemplar(
        id=uuid4(),
        obra_id=obra_id,
        codigo_qr="QR-002",
        estado="emprestado",
        localizacao_estante="A2",
        created_at=created_at,
    )
    exemplar_baixado = Exemplar(
        id=uuid4(),
        obra_id=obra_id,
        codigo_qr="QR-003",
        estado="baixado",
        localizacao_estante="A3",
        created_at=created_at,
    )

    assert exemplar_disponivel.estado == "disponivel"
    assert exemplar_emprestado.estado == "emprestado"
    assert exemplar_baixado.estado == "baixado"
