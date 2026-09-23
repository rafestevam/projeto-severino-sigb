"""
Testes unitários para alembic/versions/d123456789ab_0004_add_configuracao.py

Estratégia: carregar o módulo de migration via importlib.util
e substituir `alembic.op` por mocks em cada teste — sem banco de dados.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

_MIGRATION_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "alembic" / "versions" / "d123456789ab_0004_add_configuracao.py"
)
_MODULE_NAME = "migration_0004_add_configuracao"


@pytest.fixture(scope="module")
def migration() -> ModuleType:
    sys.modules.pop(_MODULE_NAME, None)
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, _MIGRATION_FILE)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class TestMigrationMetadata:
    def test_revision_id(self, migration: ModuleType) -> None:
        assert migration.revision == "d123456789ab"

    def test_down_revision_aponta_para_0003(self, migration: ModuleType) -> None:
        assert migration.down_revision == "c123456789ab"

    def test_branch_labels_e_none(self, migration: ModuleType) -> None:
        assert migration.branch_labels is None

    def test_depends_on_e_none(self, migration: ModuleType) -> None:
        assert migration.depends_on is None


@pytest.fixture(autouse=True)
def _patch_op_f():
    with patch("alembic.op.f", side_effect=lambda name: name):
        yield


class TestMigrationUpgrade:
    def test_create_table_e_bulk_insert_chamados(self, migration: ModuleType) -> None:
        with patch("alembic.op.create_table") as mock_create, \
             patch("alembic.op.create_index") as mock_idx, \
             patch("alembic.op.bulk_insert") as mock_bulk:
            mock_table = MagicMock()
            mock_create.return_value = mock_table

            migration.upgrade()

            mock_create.assert_called_once()
            assert mock_create.call_args[0][0] == "configuracao"

            mock_idx.assert_called_once()
            assert mock_idx.call_args[0][1] == "configuracao"

            mock_bulk.assert_called_once()
            inserted_rows = mock_bulk.call_args[0][1]
            chaves = {row["chave"] for row in inserted_rows}
            valores = {row["chave"]: row["valor"] for row in inserted_rows}

            assert chaves == {"dias_emprestimo", "max_renovacoes", "max_emprestimos_por_leitor"}
            assert valores["dias_emprestimo"] == "14"
            assert valores["max_renovacoes"] == "3"
            assert valores["max_emprestimos_por_leitor"] == "3"


class TestMigrationDowngrade:
    def test_drop_index_e_table(self, migration: ModuleType) -> None:
        with patch("alembic.op.drop_index") as mock_drop_idx, \
             patch("alembic.op.drop_table") as mock_drop_tbl:
            migration.downgrade()

            mock_drop_idx.assert_called_once_with("ix_configuracao_chave", table_name="configuracao")
            mock_drop_tbl.assert_called_once_with("configuracao")
