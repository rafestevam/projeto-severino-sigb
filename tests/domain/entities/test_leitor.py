import hashlib
from datetime import datetime
from uuid import uuid4

from app.domain.entities import Leitor


def test_leitor_instantiation_sets_all_attributes() -> None:
    leitor_id = uuid4()
    created_at = datetime(2024, 1, 10, 14, 30)

    leitor = Leitor(
        id=leitor_id,
        nome="Maria Silva",
        cpf_hash="abc123",
        telefone="11999999999",
        email="maria@example.com",
        ativo=True,
        created_at=created_at,
    )

    assert leitor.id == leitor_id
    assert leitor.nome == "Maria Silva"
    assert leitor.cpf_hash == "abc123"
    assert leitor.telefone == "11999999999"
    assert leitor.email == "maria@example.com"
    assert leitor.ativo is True
    assert leitor.created_at == created_at


def test_leitor_hash_cpf_returns_expected_sha256_hash() -> None:
    cpf = "12345678900"
    expected_hash = hashlib.sha256(cpf.encode()).hexdigest()

    assert Leitor.hash_cpf(cpf) == expected_hash
    assert Leitor.hash_cpf(cpf) == expected_hash
