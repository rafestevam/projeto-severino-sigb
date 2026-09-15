"""
Testes unitários para app/adapters/repositories/models/leitor.py

Estratégia: inspecionar diretamente o metadata da tabela gerado pelo SQLAlchemy
sem abrir conexão com banco de dados. Todos os testes são puramente síncronos
e não requerem nenhum serviço externo.
"""
from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, String

from app.adapters.repositories.models.leitor import LeitorModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_column(name: str) -> sa.Column:
    """Retorna a Column pelo nome na tabela leitor."""
    table = LeitorModel.__table__
    assert name in table.c, f"Coluna '{name}' não encontrada na tabela leitor"
    return table.c[name]


# ---------------------------------------------------------------------------
# Tabela e mapeamento ORM
# ---------------------------------------------------------------------------

class TestLeitorModelTableName:
    def test_tablename_e_leitor(self) -> None:
        assert LeitorModel.__tablename__ == "leitor"

    def test_table_registrada_no_metadata(self) -> None:
        from app.infrastructure.database import Base

        assert "leitor" in Base.metadata.tables


# ---------------------------------------------------------------------------
# Coluna id
# ---------------------------------------------------------------------------

class TestLeitorModelColumnId:
    def test_id_e_chave_primaria(self) -> None:
        col = _get_column("id")
        assert col.primary_key is True

    def test_id_e_uuid(self) -> None:
        col = _get_column("id")
        # O tipo é UUID do dialeto PostgreSQL — verificamos via string do tipo
        assert "UUID" in type(col.type).__name__.upper()

    def test_id_tem_default_uuid4(self) -> None:
        """O default deve ser o callable uuid.uuid4 (gera UUIDs sem banco)."""
        col = _get_column("id")
        # SQLAlchemy envolve o callable numa ColumnDefault; .arg é o callable original.
        # Verificamos por nome/módulo porque o objeto pode diferir entre imports.
        fn = col.default.arg  # type: ignore[union-attr]
        assert fn.__name__ == "uuid4" and fn.__module__ == "uuid"


# ---------------------------------------------------------------------------
# Coluna nome
# ---------------------------------------------------------------------------

class TestLeitorModelColumnNome:
    def test_nome_nao_e_nullable(self) -> None:
        assert _get_column("nome").nullable is False

    def test_nome_e_string_256(self) -> None:
        col = _get_column("nome")
        assert isinstance(col.type, String)
        assert col.type.length == 256


# ---------------------------------------------------------------------------
# Coluna cpf_hash (regra de privacidade central da US-006)
# ---------------------------------------------------------------------------

class TestLeitorModelColumnCpfHash:
    def test_cpf_hash_existe(self) -> None:
        _get_column("cpf_hash")  # levanta AssertionError se não existir

    def test_cpf_hash_e_string_64(self) -> None:
        col = _get_column("cpf_hash")
        assert isinstance(col.type, String)
        assert col.type.length == 64

    def test_cpf_hash_nao_e_nullable(self) -> None:
        assert _get_column("cpf_hash").nullable is False

    def test_cpf_hash_tem_indice(self) -> None:
        """US-006: o campo cpf_hash deve ter índice para lookup eficiente."""
        col = _get_column("cpf_hash")
        assert col.index is True

    def test_coluna_cpf_nao_existe(self) -> None:
        """O CPF original jamais deve ser persistido (US-006)."""
        assert "cpf" not in LeitorModel.__table__.c


# ---------------------------------------------------------------------------
# Coluna telefone
# ---------------------------------------------------------------------------

class TestLeitorModelColumnTelefone:
    def test_telefone_e_nullable(self) -> None:
        assert _get_column("telefone").nullable is True

    def test_telefone_e_string_32(self) -> None:
        col = _get_column("telefone")
        assert isinstance(col.type, String)
        assert col.type.length == 32


# ---------------------------------------------------------------------------
# Coluna email
# ---------------------------------------------------------------------------

class TestLeitorModelColumnEmail:
    def test_email_nao_e_nullable(self) -> None:
        assert _get_column("email").nullable is False

    def test_email_e_string_256(self) -> None:
        col = _get_column("email")
        assert isinstance(col.type, String)
        assert col.type.length == 256


# ---------------------------------------------------------------------------
# Coluna ativo
# ---------------------------------------------------------------------------

class TestLeitorModelColumnAtivo:
    def test_ativo_e_boolean(self) -> None:
        col = _get_column("ativo")
        assert isinstance(col.type, Boolean)

    def test_ativo_nao_e_nullable(self) -> None:
        assert _get_column("ativo").nullable is False

    def test_ativo_tem_default_true(self) -> None:
        col = _get_column("ativo")
        assert col.default.arg is True  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Coluna created_at
# ---------------------------------------------------------------------------

class TestLeitorModelColumnCreatedAt:
    def test_created_at_e_datetime_com_timezone(self) -> None:
        col = _get_column("created_at")
        assert isinstance(col.type, DateTime)
        assert col.type.timezone is True

    def test_created_at_nao_e_nullable(self) -> None:
        assert _get_column("created_at").nullable is False

    def test_created_at_tem_server_default(self) -> None:
        col = _get_column("created_at")
        assert col.server_default is not None


# ---------------------------------------------------------------------------
# Inventário completo de colunas
# ---------------------------------------------------------------------------

class TestLeitorModelColumns:
    def test_conjunto_exato_de_colunas(self) -> None:
        expected = {"id", "nome", "cpf_hash", "telefone", "email", "ativo", "created_at"}
        actual = set(LeitorModel.__table__.c.keys())
        assert actual == expected
