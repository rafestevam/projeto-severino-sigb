"""
Testes unitários para app/adapters/repositories/models/configuracao.py

Estratégia: inspecionar diretamente o metadata da tabela gerado pelo SQLAlchemy
sem abrir conexão com banco de dados. Todos os testes são puramente síncronos
e não requerem nenhum serviço externo.
"""
from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy import DateTime, String

from app.adapters.repositories.models.configuracao import ConfiguracaoModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_column(name: str) -> sa.Column:
    """Retorna a Column pelo nome na tabela configuracao."""
    table = ConfiguracaoModel.__table__
    assert name in table.c, f"Coluna '{name}' não encontrada na tabela configuracao"
    return table.c[name]


# ---------------------------------------------------------------------------
# Tabela e mapeamento ORM
# ---------------------------------------------------------------------------


class TestConfiguracaoModelTableName:
    def test_tablename_e_configuracao(self) -> None:
        assert ConfiguracaoModel.__tablename__ == "configuracao"

    def test_table_registrada_no_metadata(self) -> None:
        from app.infrastructure.database import Base

        assert "configuracao" in Base.metadata.tables


# ---------------------------------------------------------------------------
# Coluna id
# ---------------------------------------------------------------------------


class TestConfiguracaoModelColumnId:
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
# Coluna chave
# ---------------------------------------------------------------------------


class TestConfiguracaoModelColumnChave:
    def test_chave_existe(self) -> None:
        _get_column("chave")  # levanta AssertionError se não existir

    def test_chave_e_string_100(self) -> None:
        col = _get_column("chave")
        assert isinstance(col.type, String)
        assert col.type.length == 100

    def test_chave_nao_e_nullable(self) -> None:
        assert _get_column("chave").nullable is False

    def test_chave_tem_indice_unico(self) -> None:
        """A coluna chave deve ser única (UNIQUE constraint + índice)."""
        col = _get_column("chave")
        assert col.unique is True
        assert col.index is True


# ---------------------------------------------------------------------------
# Coluna valor
# ---------------------------------------------------------------------------


class TestConfiguracaoModelColumnValor:
    def test_valor_existe(self) -> None:
        _get_column("valor")  # levanta AssertionError se não existir

    def test_valor_e_string_255(self) -> None:
        col = _get_column("valor")
        assert isinstance(col.type, String)
        assert col.type.length == 255

    def test_valor_nao_e_nullable(self) -> None:
        assert _get_column("valor").nullable is False


# ---------------------------------------------------------------------------
# Coluna updated_at
# ---------------------------------------------------------------------------


class TestConfiguracaoModelColumnUpdatedAt:
    def test_updated_at_e_datetime_com_timezone(self) -> None:
        col = _get_column("updated_at")
        assert isinstance(col.type, DateTime)
        assert col.type.timezone is True

    def test_updated_at_nao_e_nullable(self) -> None:
        assert _get_column("updated_at").nullable is False

    def test_updated_at_tem_server_default(self) -> None:
        col = _get_column("updated_at")
        assert col.server_default is not None

    def test_updated_at_tem_onupdate(self) -> None:
        col = _get_column("updated_at")
        assert col.onupdate is not None


# ---------------------------------------------------------------------------
# Inventário completo de colunas
# ---------------------------------------------------------------------------


class TestConfiguracaoModelColumns:
    def test_conjunto_exato_de_colunas(self) -> None:
        expected = {"id", "chave", "valor", "updated_at"}
        actual = set(ConfiguracaoModel.__table__.c.keys())
        assert actual == expected

    def test_constraints_unicos(self) -> None:
        """Verifica que a constraint UNIQUE na coluna chave existe (implementada como índice único)."""
        table = ConfiguracaoModel.__table__
        unique_indexes = [idx for idx in table.indexes if idx.unique]
        assert len(unique_indexes) == 1
        ui = unique_indexes[0]
        assert set(ui.columns.keys()) == {"chave"}