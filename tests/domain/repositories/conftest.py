"""
Fixtures compartilhadas para os testes dos repositórios de domínio.

Fornece construtores de entidades prontos para uso em cada suite de testes,
evitando repetição de código sem precisar de banco de dados ou I/O externo.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from app.domain.entities.emprestimo import Emprestimo
from app.domain.entities.exemplar import Exemplar
from app.domain.entities.leitor import Leitor
from app.domain.entities.obra import Obra
from app.domain.entities.reserva import Reserva

# ---------------------------------------------------------------------------
# UUIDs fixos para facilitar asserções de identidade entre testes
# ---------------------------------------------------------------------------
OBRA_ID: UUID = uuid4()
EXEMPLAR_ID: UUID = uuid4()
LEITOR_ID: UUID = uuid4()
EMPRESTIMO_ID: UUID = uuid4()
RESERVA_ID: UUID = uuid4()

CREATED_AT: datetime = datetime(2024, 3, 15, 10, 0, 0)
DATA_CHECKOUT: datetime = datetime(2024, 3, 15, 10, 0, 0)
DATA_PREVISTA: datetime = datetime(2024, 3, 22, 10, 0, 0)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def make_obra(
    *,
    id: UUID = OBRA_ID,
    isbn: str = "9788575228289",
    titulo: str = "Clean Architecture",
    autores: list[str] | None = None,
    editora: str = "Alta Books",
    ano: int = 2018,
    capa_url: str = "https://example.com/capa.jpg",
    categoria: str = "Arquitetura de Software",
    created_at: datetime = CREATED_AT,
) -> Obra:
    return Obra(
        id=id,
        isbn=isbn,
        titulo=titulo,
        autores=autores if autores is not None else ["Robert C. Martin"],
        editora=editora,
        ano=ano,
        capa_url=capa_url,
        categoria=categoria,
        created_at=created_at,
    )


def make_exemplar(
    *,
    id: UUID = EXEMPLAR_ID,
    obra_id: UUID = OBRA_ID,
    codigo_qr: str = "QR-001",
    estado: str = "disponivel",
    localizacao_estante: str = "A1",
    created_at: datetime = CREATED_AT,
) -> Exemplar:
    return Exemplar(
        id=id,
        obra_id=obra_id,
        codigo_qr=codigo_qr,
        estado=estado,  # type: ignore[arg-type]
        localizacao_estante=localizacao_estante,
        created_at=created_at,
    )


def make_leitor(
    *,
    id: UUID = LEITOR_ID,
    nome: str = "Maria Silva",
    cpf_hash: str = Leitor.hash_cpf("12345678900"),
    telefone: str = "11999999999",
    email: str = "maria@example.com",
    ativo: bool = True,
    created_at: datetime = CREATED_AT,
) -> Leitor:
    return Leitor(
        id=id,
        nome=nome,
        cpf_hash=cpf_hash,
        telefone=telefone,
        email=email,
        ativo=ativo,
        created_at=created_at,
    )


def make_emprestimo(
    *,
    id: UUID = EMPRESTIMO_ID,
    exemplar_id: UUID = EXEMPLAR_ID,
    leitor_id: UUID = LEITOR_ID,
    data_checkout: datetime = DATA_CHECKOUT,
    data_prevista: datetime = DATA_PREVISTA,
    data_devolucao: datetime | None = None,
    renovacoes: int = 0,
    status: str = "ativo",
) -> Emprestimo:
    return Emprestimo(
        id=id,
        exemplar_id=exemplar_id,
        leitor_id=leitor_id,
        data_checkout=data_checkout,
        data_prevista=data_prevista,
        data_devolucao=data_devolucao,
        renovacoes=renovacoes,
        status=status,  # type: ignore[arg-type]
    )


def make_reserva(
    *,
    id: UUID = RESERVA_ID,
    obra_id: UUID = OBRA_ID,
    leitor_id: UUID = LEITOR_ID,
    status: str = "aguardando",
    created_at: datetime = CREATED_AT,
) -> Reserva:
    return Reserva(
        id=id,
        obra_id=obra_id,
        leitor_id=leitor_id,
        status=status,  # type: ignore[arg-type]
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def obra() -> Obra:
    return make_obra()


@pytest.fixture
def exemplar() -> Exemplar:
    return make_exemplar()


@pytest.fixture
def leitor() -> Leitor:
    return make_leitor()


@pytest.fixture
def emprestimo() -> Emprestimo:
    return make_emprestimo()


@pytest.fixture
def reserva() -> Reserva:
    return make_reserva()
