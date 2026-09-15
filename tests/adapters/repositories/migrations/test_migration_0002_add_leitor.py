"""
Testes unitários para alembic/versions/b9cb64000fbf_0002_add_leitor.py

Estratégia: carregar o módulo de migration uma única vez via importlib.util
(sem depender de alembic.versions como pacote instalado) e substituir
`alembic.op` por mocks em cada teste — sem banco de dados.

O módulo faz `from alembic import op` em tempo de execução, o que vincula
`op` ao objeto `alembic.op` em sys.modules.  Ao usar patch("alembic.op.*"),
o mock substitui os atributos nesse mesmo objeto, portanto o módulo já
carregado vê os mocks corretamente.
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
    / "alembic" / "versions" / "b9cb64000fbf_0002_add_leitor.py"
)
_MODULE_NAME = "migration_0002_add_leitor"


# ---------------------------------------------------------------------------
# Fixture: carrega o módulo uma vez por sessão de testes
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def migration() -> ModuleType:
    """Carrega o arquivo de migration como módulo Python sem precisar que
    alembic/versions seja um pacote instalado."""
    sys.modules.pop(_MODULE_NAME, None)
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, _MIGRATION_FILE)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Metadados da revisão
# ---------------------------------------------------------------------------

class TestMigrationMetadata:
    def test_revision_id(self, migration: ModuleType) -> None:
        assert migration.revision == "b9cb64000fbf"

    def test_down_revision_aponta_para_0001(self, migration: ModuleType) -> None:
        """A chain deve ser 0002 → 0001; qualquer outra quebra a sequência."""
        assert migration.down_revision == "1ff02fc52fd6"

    def test_branch_labels_e_none(self, migration: ModuleType) -> None:
        assert migration.branch_labels is None

    def test_depends_on_e_none(self, migration: ModuleType) -> None:
        assert migration.depends_on is None


# ---------------------------------------------------------------------------
# Fixture shared by upgrade/downgrade tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_op_f():
    """op.f(name) é um helper de naming que exige um proxy Alembic inicializado
    — o que só existe durante uma migration real.  Substituímos por uma função
    identidade para que os testes possam chamar upgrade()/downgrade() sem banco."""
    with patch("alembic.op.f", side_effect=lambda name: name):
        yield


# ---------------------------------------------------------------------------
# upgrade() — verificação dos comandos DDL emitidos
# ---------------------------------------------------------------------------

class TestMigrationUpgrade:
    def test_create_table_e_chamado_com_nome_leitor(self, migration: ModuleType) -> None:
        with patch("alembic.op.create_table") as mock_create, \
             patch("alembic.op.create_index"):
            migration.upgrade()
            assert mock_create.call_args[0][0] == "leitor"

    def test_create_table_define_sete_colunas(self, migration: ModuleType) -> None:
        """upgrade() deve declarar exatamente as 7 colunas exigidas."""
        with patch("alembic.op.create_table") as mock_create, \
             patch("alembic.op.create_index"):
            migration.upgrade()
            import sqlalchemy as sa
            pos_args = mock_create.call_args[0]
            cols = [a for a in pos_args[1:] if isinstance(a, sa.Column)]
            col_names = {c.name for c in cols}
            expected = {"id", "nome", "cpf_hash", "telefone", "email", "ativo", "created_at"}
            assert col_names == expected

    def test_cpf_hash_e_string_64(self, migration: ModuleType) -> None:
        with patch("alembic.op.create_table") as mock_create, \
             patch("alembic.op.create_index"):
            migration.upgrade()
            import sqlalchemy as sa
            pos_args = mock_create.call_args[0]
            cols = {c.name: c for c in pos_args[1:] if isinstance(c, sa.Column)}
            col = cols["cpf_hash"]
            assert isinstance(col.type, sa.String)
            assert col.type.length == 64

    def test_cpf_hash_nao_e_nullable(self, migration: ModuleType) -> None:
        with patch("alembic.op.create_table") as mock_create, \
             patch("alembic.op.create_index"):
            migration.upgrade()
            import sqlalchemy as sa
            pos_args = mock_create.call_args[0]
            cols = {c.name: c for c in pos_args[1:] if isinstance(c, sa.Column)}
            assert cols["cpf_hash"].nullable is False

    def test_coluna_cpf_nao_declarada(self, migration: ModuleType) -> None:
        """O CPF original jamais deve aparecer na migration (US-006)."""
        with patch("alembic.op.create_table") as mock_create, \
             patch("alembic.op.create_index"):
            migration.upgrade()
            import sqlalchemy as sa
            pos_args = mock_create.call_args[0]
            col_names = {
                c.name for c in pos_args[1:] if isinstance(c, sa.Column)
            }
            assert "cpf" not in col_names

    def test_telefone_e_nullable(self, migration: ModuleType) -> None:
        with patch("alembic.op.create_table") as mock_create, \
             patch("alembic.op.create_index"):
            migration.upgrade()
            import sqlalchemy as sa
            pos_args = mock_create.call_args[0]
            cols = {c.name: c for c in pos_args[1:] if isinstance(c, sa.Column)}
            assert cols["telefone"].nullable is True

    def test_ativo_e_boolean(self, migration: ModuleType) -> None:
        with patch("alembic.op.create_table") as mock_create, \
             patch("alembic.op.create_index"):
            migration.upgrade()
            import sqlalchemy as sa
            pos_args = mock_create.call_args[0]
            cols = {c.name: c for c in pos_args[1:] if isinstance(c, sa.Column)}
            assert isinstance(cols["ativo"].type, sa.Boolean)
            assert cols["ativo"].nullable is False

    def test_created_at_e_datetime_com_timezone(self, migration: ModuleType) -> None:
        with patch("alembic.op.create_table") as mock_create, \
             patch("alembic.op.create_index"):
            migration.upgrade()
            import sqlalchemy as sa
            pos_args = mock_create.call_args[0]
            cols = {c.name: c for c in pos_args[1:] if isinstance(c, sa.Column)}
            col = cols["created_at"]
            assert isinstance(col.type, sa.DateTime)
            assert col.type.timezone is True

    def test_created_at_tem_server_default_now(self, migration: ModuleType) -> None:
        with patch("alembic.op.create_table") as mock_create, \
             patch("alembic.op.create_index"):
            migration.upgrade()
            import sqlalchemy as sa
            pos_args = mock_create.call_args[0]
            cols = {c.name: c for c in pos_args[1:] if isinstance(c, sa.Column)}
            sd = cols["created_at"].server_default
            assert sd is not None
            assert "now()" in str(sd.arg)  # type: ignore[union-attr]

    def test_primary_key_constraint_em_id(self, migration: ModuleType) -> None:
        with patch("alembic.op.create_table") as mock_create, \
             patch("alembic.op.create_index"):
            migration.upgrade()
            import sqlalchemy as sa
            pos_args = mock_create.call_args[0]
            pk_constraints = [
                a for a in pos_args[1:]
                if isinstance(a, sa.PrimaryKeyConstraint)
            ]
            assert len(pk_constraints) == 1
            # Fora de um contexto de tabela real, os nomes de coluna ficam em
            # _pending_colargs (strings) antes de serem resolvidos como Column objects.
            pending = pk_constraints[0]._pending_colargs
            assert "id" in pending

    def test_create_index_chamado_para_cpf_hash(self, migration: ModuleType) -> None:
        """US-006: índice em cpf_hash é obrigatório para lookup eficiente."""
        with patch("alembic.op.create_table"), \
             patch("alembic.op.create_index") as mock_idx:
            migration.upgrade()
            mock_idx.assert_called_once()
            call_args = mock_idx.call_args
            # Segundo argumento posicional é o nome da tabela
            assert call_args[0][1] == "leitor"
            # Terceiro argumento é a lista de colunas indexadas
            assert call_args[0][2] == ["cpf_hash"]

    def test_create_index_nao_e_unico(self, migration: ModuleType) -> None:
        """O índice em cpf_hash deve ser não-único (apenas para lookup)."""
        with patch("alembic.op.create_table"), \
             patch("alembic.op.create_index") as mock_idx:
            migration.upgrade()
            call_kwargs = mock_idx.call_args[1]
            assert call_kwargs.get("unique") is False


# ---------------------------------------------------------------------------
# downgrade() — verificação da reversibilidade
# ---------------------------------------------------------------------------

class TestMigrationDowngrade:
    def test_drop_index_chamado_antes_de_drop_table(self, migration: ModuleType) -> None:
        """O índice deve ser removido antes da tabela (integridade DDL)."""
        call_order: list[str] = []

        with patch("alembic.op.drop_index",  side_effect=lambda *a, **kw: call_order.append("drop_index")), \
             patch("alembic.op.drop_table",  side_effect=lambda *a, **kw: call_order.append("drop_table")):
            migration.downgrade()

        assert call_order == ["drop_index", "drop_table"]

    def test_drop_index_aponta_para_tabela_leitor(self, migration: ModuleType) -> None:
        with patch("alembic.op.drop_index") as mock_drop_idx, \
             patch("alembic.op.drop_table"):
            migration.downgrade()
            call_kwargs = mock_drop_idx.call_args[1]
            assert call_kwargs.get("table_name") == "leitor"

    def test_drop_table_remove_tabela_leitor(self, migration: ModuleType) -> None:
        with patch("alembic.op.drop_index"), \
             patch("alembic.op.drop_table") as mock_drop_table:
            migration.downgrade()
            mock_drop_table.assert_called_once_with("leitor")

    def test_downgrade_nao_chama_create_table(self, migration: ModuleType) -> None:
        with patch("alembic.op.drop_index"), \
             patch("alembic.op.drop_table"), \
             patch("alembic.op.create_table") as mock_create:
            migration.downgrade()
            mock_create.assert_not_called()


# ---------------------------------------------------------------------------
# Simetria upgrade / downgrade
# ---------------------------------------------------------------------------

class TestMigrationSymmetry:
    def test_upgrade_e_downgrade_chamam_operacoes_opostas(self, migration: ModuleType) -> None:
        """Garante que upgrade cria e downgrade destrói — sem efeitos extras."""
        with patch("alembic.op.create_table") as mock_ct, \
             patch("alembic.op.create_index") as mock_ci, \
             patch("alembic.op.drop_table") as mock_dt, \
             patch("alembic.op.drop_index") as mock_di:
            migration.upgrade()
            assert mock_ct.call_count == 1
            assert mock_ci.call_count == 1
            assert mock_dt.call_count == 0
            assert mock_di.call_count == 0

        with patch("alembic.op.create_table") as mock_ct, \
             patch("alembic.op.create_index") as mock_ci, \
             patch("alembic.op.drop_table") as mock_dt, \
             patch("alembic.op.drop_index") as mock_di:
            migration.downgrade()
            assert mock_ct.call_count == 0
            assert mock_ci.call_count == 0
            assert mock_dt.call_count == 1
            assert mock_di.call_count == 1
