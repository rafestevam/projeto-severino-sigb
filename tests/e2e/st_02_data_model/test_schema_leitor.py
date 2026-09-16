"""
Testes de integração — ST-02 Validação do Schema: Leitor e Privacidade de CPF (US-006).
Casos cobertos: LEI-001 a LEI-008.
"""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.adapters.repositories.models.leitor import LeitorModel
from app.domain.entities.leitor import Leitor

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_lei_001_stores_only_cpf_hash_no_cpf_column(db_session: AsyncSession, db_connection: AsyncConnection):
    """LEI-001: Inserir leitor armazena apenas cpf_hash — nunca o CPF original."""
    cpf_teste = "12345678900"
    cpf_hash_calculado = Leitor.hash_cpf(cpf_teste)

    leitor = LeitorModel(
        id=uuid.uuid4(),
        nome="João da Silva",
        cpf_hash=cpf_hash_calculado,
        telefone="11988887777",
        email="joao@example.com",
        ativo=True,
    )
    db_session.add(leitor)
    await db_session.flush()

    saved = await db_session.get(LeitorModel, leitor.id)
    assert saved is not None
    assert saved.cpf_hash == cpf_hash_calculado
    assert not hasattr(saved, "cpf"), "Model Leitor não deve ter atributo cpf"

    # Verifica a nível de banco de dados (colunas da tabela leitor)
    result = await db_connection.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name = 'leitor'")
    )
    columns = {row[0] for row in result.fetchall()}
    assert "cpf" not in columns, "Coluna 'cpf' não deve existir na tabela leitor"
    assert "cpf_hash" in columns, "Coluna 'cpf_hash' deve existir na tabela leitor"


async def test_lei_002_lookup_by_cpf_hash(db_session: AsyncSession):
    """LEI-002: Buscar leitor pelo hash do CPF retorna o registro correto."""
    cpf = "12345678900"
    cpf_hash = Leitor.hash_cpf(cpf)

    leitor = LeitorModel(
        id=uuid.uuid4(),
        nome="Maria Oliveira",
        cpf_hash=cpf_hash,
        telefone="11977776666",
        email="maria@example.com",
        ativo=True,
    )
    db_session.add(leitor)
    await db_session.flush()

    # Busca calculando o hash
    search_hash = Leitor.hash_cpf("12345678900")
    result = await db_session.execute(
        select(LeitorModel).where(LeitorModel.cpf_hash == search_hash)
    )
    found = result.scalar_one_or_none()

    assert found is not None
    assert found.id == leitor.id
    assert found.nome == "Maria Oliveira"


async def test_lei_003_different_cpfs_produce_different_hashes(db_session: AsyncSession):
    """LEI-003: Dois CPFs diferentes geram hashes diferentes e buscas distintas."""
    cpf1 = "11111111111"
    cpf2 = "22222222222"

    hash1 = Leitor.hash_cpf(cpf1)
    hash2 = Leitor.hash_cpf(cpf2)
    assert hash1 != hash2

    leitor1 = LeitorModel(
        id=uuid.uuid4(),
        nome="Leitor Um",
        cpf_hash=hash1,
        telefone="111111111",
        email="l1@example.com",
        ativo=True,
    )
    leitor2 = LeitorModel(
        id=uuid.uuid4(),
        nome="Leitor Dois",
        cpf_hash=hash2,
        telefone="222222222",
        email="l2@example.com",
        ativo=True,
    )
    db_session.add_all([leitor1, leitor2])
    await db_session.flush()

    res1 = await db_session.execute(select(LeitorModel).where(LeitorModel.cpf_hash == hash1))
    assert res1.scalar_one_or_none().nome == "Leitor Um"

    res2 = await db_session.execute(select(LeitorModel).where(LeitorModel.cpf_hash == hash2))
    assert res2.scalar_one_or_none().nome == "Leitor Dois"


async def test_lei_004_hash_is_deterministic_without_salt():
    """LEI-004: Mesmo CPF sempre gera o mesmo hash (determinismo sem salt)."""
    cpf = "55566677788"
    hash_a = Leitor.hash_cpf(cpf)
    hash_b = Leitor.hash_cpf(cpf)

    assert hash_a == hash_b
    assert len(hash_a) == 64  # SHA-256 hex string


async def test_lei_005_telefone_nullable(db_session: AsyncSession):
    """LEI-005: Inserir leitor com telefone = NULL não lança erro."""
    leitor = LeitorModel(
        id=uuid.uuid4(),
        nome="Sem Telefone",
        cpf_hash=Leitor.hash_cpf("33344455566"),
        telefone=None,
        email="semtelefone@example.com",
        ativo=True,
    )
    db_session.add(leitor)
    await db_session.flush()

    saved = await db_session.get(LeitorModel, leitor.id)
    assert saved is not None
    assert saved.telefone is None


async def test_lei_006_deactivating_reader_keeps_record(db_session: AsyncSession):
    """LEI-006: Marcar ativo = False não remove o registro do banco."""
    leitor = LeitorModel(
        id=uuid.uuid4(),
        nome="Leitor Desativado",
        cpf_hash=Leitor.hash_cpf("44455566677"),
        telefone="11999998888",
        email="desativado@example.com",
        ativo=True,
    )
    db_session.add(leitor)
    await db_session.flush()

    # Atualiza ativo para False
    leitor.ativo = False
    await db_session.flush()

    saved = await db_session.get(LeitorModel, leitor.id)
    assert saved is not None
    assert saved.ativo is False


async def test_lei_007_insert_inactive_reader(db_session: AsyncSession):
    """LEI-007: Inserir leitor com ativo = False persiste corretamente."""
    leitor = LeitorModel(
        id=uuid.uuid4(),
        nome="Ja Inativo",
        cpf_hash=Leitor.hash_cpf("66677788899"),
        telefone=None,
        email="inativo@example.com",
        ativo=False,
    )
    db_session.add(leitor)
    await db_session.flush()

    saved = await db_session.get(LeitorModel, leitor.id)
    assert saved is not None
    assert saved.ativo is False


async def test_lei_008_cpf_hash_index_exists_in_database(db_connection: AsyncConnection):
    """LEI-008: O índice em cpf_hash existe em pg_indexes."""
    result = await db_connection.execute(
        text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'leitor'")
    )
    indexes = result.fetchall()
    index_defs = [row[1] for row in indexes]

    # Verifica se algum índice cobre a coluna cpf_hash
    has_cpf_hash_index = any("cpf_hash" in indexdef for indexdef in index_defs)
    assert has_cpf_hash_index, f"Índice em cpf_hash não encontrado na tabela leitor. Índices existentes: {indexes}"
