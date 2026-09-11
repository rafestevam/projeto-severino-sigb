"""
Testes unitários para alembic/versions/c123456789ab_0003_add_emprestimo_reserva_inventario_log.py

Estratégia: carregar o módulo de migration uma única vez via importlib.util
e substituir `alembic.op` por mocks em cada teste — sem banco de dados.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# Caminho absoluto para o arquivo de migration — independente do cwd.
_MIGRATION_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "alembic" / "versions" / "c123456789ab_0003_add_emprestimo_reserva_inventario_log.py"
)
_MODULE_NAME = "migration_0003_add_emprestimo_reserva"


@pytest.fixture(scope="module")
def migration() -> ModuleType:
    """Carrega o arquivo de migration como módulo Python sem precisar que
    alembic/versions seja um pacote instalado."""
    sys.modules.pop(_MODULE_NAME, None)
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, _MIGRATION_FILE)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class TestMigrationMetadata:
    def test_revision_id(self, migration: ModuleType) -> None:
        assert migration.revision == "c123456789ab"

    def test_down_revision_aponta_para_leitor(self, migration: ModuleType) -> None:
        assert migration.down_revision == "b9cb64000fbf"

    def test_branch_labels_e_none(self, migration: ModuleType) -> None:
        assert migration.branch_labels is None

    def test_depends_on_e_none(self, migration: ModuleType) -> None:
        assert migration.depends_on is None


@pytest.fixture(autouse=True)
def _patch_op_f():
    with patch("alembic.op.f", side_effect=lambda name: name):
        yield


class TestMigrationUpgrade:
    def test_create_tables_sao_chamados(self, migration: ModuleType) -> None:
        with patch("alembic.op.create_table") as mock_create, \
             patch("alembic.op.create_index"), \
             patch("alembic.op.execute"):
            migration.upgrade()
            created_tables = [call[0][0] for call in mock_create.call_args_list]
            assert "emprestimo" in created_tables
            assert "reserva" in created_tables
            assert "inventario_log" in created_tables

    def test_executes_check_types(self, migration: ModuleType) -> None:
        with patch("alembic.op.create_table"), \
             patch("alembic.op.create_index"), \
             patch("alembic.op.execute") as mock_exec:
            migration.upgrade()
            executed_cmds = [call[0][0] for call in mock_exec.call_args_list]
            # Verify they run conditional check for type creations
            assert any("statusemprestimo" in cmd for cmd in executed_cmds)
            assert any("statusreserva" in cmd for cmd in executed_cmds)
            assert any("acaoinventariolog" in cmd for cmd in executed_cmds)


class TestMigrationDowngrade:
    def test_drop_indices_e_tables(self, migration: ModuleType) -> None:
        with patch("alembic.op.drop_index") as mock_drop_idx, \
             patch("alembic.op.drop_table") as mock_drop_tbl, \
             patch("alembic.op.execute") as mock_exec:
            migration.downgrade()
            dropped_tables = [call[0][0] for call in mock_drop_tbl.call_args_list]
            assert "emprestimo" in dropped_tables
            assert "reserva" in dropped_tables
            assert "inventario_log" in dropped_tables

            executed_cmds = [call[0][0] for call in mock_exec.call_args_list]
            assert any("DROP TYPE IF EXISTS statusemprestimo" in cmd for cmd in executed_cmds)
            assert any("DROP TYPE IF EXISTS statusreserva" in cmd for cmd in executed_cmds)
            assert any("DROP TYPE IF EXISTS acaoinventariolog" in cmd for cmd in executed_cmds)
