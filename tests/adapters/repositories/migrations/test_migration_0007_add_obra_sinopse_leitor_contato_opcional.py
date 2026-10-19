"""
Testes unitários para alembic/versions/a7b8c9d0e1f2_0007_add_obra_sinopse_leitor_contato_opcional.py

Estratégia: carregar o módulo de migration via importlib.util
e substituir `alembic.op` por mocks em cada teste — sem banco de dados.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest

_MIGRATION_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "alembic" / "versions" / "a7b8c9d0e1f2_0007_add_obra_sinopse_leitor_contato_opcional.py"
)
_MODULE_NAME = "migration_0007_add_obra_sinopse_leitor_contato_opcional"


@pytest.fixture(scope="module")
def migration() -> ModuleType:
    sys.modules.pop(_MODULE_NAME, None)
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, _MIGRATION_FILE)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class TestMigrationMetadata:
    def test_revision_id(self, migration: ModuleType) -> None:
        assert migration.revision == "a7b8c9d0e1f2"

    def test_down_revision_aponta_para_0006(self, migration: ModuleType) -> None:
        assert migration.down_revision == "f123456789ab"


class TestMigrationUpgrade:
    def test_adiciona_sinopse_torna_email_opcional_e_cria_indice(self, migration: ModuleType) -> None:
        with patch("alembic.op.add_column") as add_column, \
             patch("alembic.op.alter_column") as alter_column, \
             patch("alembic.op.create_index") as create_index:
            migration.upgrade()

        tabela, coluna = add_column.call_args.args
        assert (tabela, coluna.name, coluna.nullable) == ("obra", "sinopse", True)

        alter_column.assert_called_once()
        assert alter_column.call_args.args == ("leitor", "email")
        assert alter_column.call_args.kwargs["nullable"] is True

        assert create_index.call_args.args[:2] == ("ix_leitor_email_lower", "leitor")
        assert "lower(email)" in str(create_index.call_args.args[2][0])


class TestMigrationDowngrade:
    def test_reverte_na_ordem_inversa_preenchendo_emails_nulos(self, migration: ModuleType) -> None:
        with patch("alembic.op.drop_index") as drop_index, \
             patch("alembic.op.execute") as execute, \
             patch("alembic.op.alter_column") as alter_column, \
             patch("alembic.op.drop_column") as drop_column:
            migration.downgrade()

        drop_index.assert_called_once_with("ix_leitor_email_lower", table_name="leitor")
        assert "email IS NULL" in execute.call_args.args[0]
        assert alter_column.call_args.kwargs["nullable"] is False
        drop_column.assert_called_once_with("obra", "sinopse")
