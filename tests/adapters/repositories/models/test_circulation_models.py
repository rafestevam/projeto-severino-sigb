"""
Testes unitários para os modelos ORM criados na sub-tarefa 7:
- EmprestimoModel
- ReservaModel
- InventarioLogModel

Estratégia: inspecionar diretamente o metadata da tabela gerado pelo SQLAlchemy
sem abrir conexão com banco de dados.
"""
from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy import DateTime, Integer, String

from app.adapters.repositories.models.emprestimo import EmprestimoModel
from app.adapters.repositories.models.reserva import ReservaModel
from app.adapters.repositories.models.inventario_log import InventarioLogModel


def _get_column(model, name: str) -> sa.Column:
    table = model.__table__
    assert name in table.c, f"Coluna '{name}' não encontrada no modelo {model.__name__}"
    return table.c[name]


class TestEmprestimoModelSchema:
    def test_tablename_e_emprestimo(self) -> None:
        assert EmprestimoModel.__tablename__ == "emprestimo"

    def test_columns(self) -> None:
        expected = {
            "id", "exemplar_id", "leitor_id", "data_checkout",
            "data_prevista", "data_devolucao", "renovacoes", "status"
        }
        actual = set(EmprestimoModel.__table__.c.keys())
        assert actual == expected

    def test_id_e_uuid_pk(self) -> None:
        col = _get_column(EmprestimoModel, "id")
        assert col.primary_key is True
        assert "UUID" in type(col.type).__name__.upper()

    def test_fk_constraints(self) -> None:
        exemplar_col = _get_column(EmprestimoModel, "exemplar_id")
        assert len(exemplar_col.foreign_keys) == 1
        fk = list(exemplar_col.foreign_keys)[0]
        assert fk.target_fullname == "exemplar.id"
        assert fk.ondelete == "RESTRICT"

        leitor_col = _get_column(EmprestimoModel, "leitor_id")
        assert len(leitor_col.foreign_keys) == 1
        fk = list(leitor_col.foreign_keys)[0]
        assert fk.target_fullname == "leitor.id"
        assert fk.ondelete == "RESTRICT"

    def test_data_checkout_datetime_with_tz(self) -> None:
        col = _get_column(EmprestimoModel, "data_checkout")
        assert isinstance(col.type, DateTime)
        assert col.type.timezone is True
        assert col.nullable is False

    def test_data_devolucao_is_nullable(self) -> None:
        col = _get_column(EmprestimoModel, "data_devolucao")
        assert col.nullable is True


class TestReservaModelSchema:
    def test_tablename_e_reserva(self) -> None:
        assert ReservaModel.__tablename__ == "reserva"

    def test_columns(self) -> None:
        expected = {"id", "obra_id", "leitor_id", "status", "created_at"}
        actual = set(ReservaModel.__table__.c.keys())
        assert actual == expected

    def test_fk_constraints(self) -> None:
        obra_col = _get_column(ReservaModel, "obra_id")
        assert len(obra_col.foreign_keys) == 1
        fk = list(obra_col.foreign_keys)[0]
        assert fk.target_fullname == "obra.id"
        assert fk.ondelete == "RESTRICT"

        leitor_col = _get_column(ReservaModel, "leitor_id")
        assert len(leitor_col.foreign_keys) == 1
        fk = list(leitor_col.foreign_keys)[0]
        assert fk.target_fullname == "leitor.id"
        assert fk.ondelete == "RESTRICT"


class TestInventarioLogModelSchema:
    def test_tablename_e_inventario_log(self) -> None:
        assert InventarioLogModel.__tablename__ == "inventario_log"

    def test_columns(self) -> None:
        expected = {"id", "exemplar_id", "operador_keycloak_id", "acao", "timestamp"}
        actual = set(InventarioLogModel.__table__.c.keys())
        assert actual == expected

    def test_fk_constraints_and_types(self) -> None:
        ex_col = _get_column(InventarioLogModel, "exemplar_id")
        assert len(ex_col.foreign_keys) == 1
        fk = list(ex_col.foreign_keys)[0]
        assert fk.target_fullname == "exemplar.id"
        assert fk.ondelete == "RESTRICT"

        op_col = _get_column(InventarioLogModel, "operador_keycloak_id")
        assert isinstance(op_col.type, String)
        assert op_col.type.length == 36
        assert len(op_col.foreign_keys) == 0  # External ID reference only
