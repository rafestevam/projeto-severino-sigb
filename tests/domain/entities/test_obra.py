from datetime import datetime
from uuid import uuid4

from app.domain.entities import Obra


def test_obra_instantiation_sets_all_attributes() -> None:
    obra_id = uuid4()
    created_at = datetime(2024, 1, 10, 14, 30)
    autores = ["Autor Um", "Autor Dois"]

    obra = Obra(
        id=obra_id,
        isbn="9788575228289",
        titulo="Clean Architecture",
        autores=autores,
        editora="Alta Books",
        ano=2018,
        capa_url="https://example.com/capa.jpg",
        categoria="Arquitetura de Software",
        created_at=created_at,
    )

    assert obra.id == obra_id
    assert obra.isbn == "9788575228289"
    assert obra.titulo == "Clean Architecture"
    assert obra.autores == autores
    assert obra.created_at == created_at
