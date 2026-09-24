"""
Testes unitários para os schemas Pydantic de empréstimo e configuração.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.adapters.api.schemas.configuracao import (
    ConfiguracaoListOut,
    ConfiguracaoOut,
    ConfiguracaoUpdateIn,
)
from app.adapters.api.schemas.emprestimo import (
    CheckoutIn,
    DevolucaoQrIn,
    EmprestimoListOut,
    EmprestimoOut,
)


class TestCheckoutIn:
    def test_valida_payload_correto(self):
        ex_id = uuid4()
        lei_id = uuid4()
        schema = CheckoutIn(exemplar_id=ex_id, leitor_id=lei_id)
        assert schema.exemplar_id == ex_id
        assert schema.leitor_id == lei_id

    def test_campos_obrigatorios(self):
        with pytest.raises(ValidationError):
            CheckoutIn(exemplar_id=uuid4())  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            CheckoutIn(leitor_id=uuid4())  # type: ignore[call-arg]


class TestDevolucaoQrIn:
    def test_valida_payload_correto(self):
        schema = DevolucaoQrIn(codigo_qr="QR12345")
        assert schema.codigo_qr == "QR12345"

    def test_campo_obrigatorio(self):
        with pytest.raises(ValidationError):
            DevolucaoQrIn()  # type: ignore[call-arg]


class TestEmprestimoOut:
    def test_valida_objeto_completo(self):
        emp_id = uuid4()
        ex_id = uuid4()
        lei_id = uuid4()
        now = datetime.now(timezone.utc)

        class MockEmprestimo:
            id = emp_id
            exemplar_id = ex_id
            leitor_id = lei_id
            titulo_obra = "Clean Architecture"
            data_checkout = now
            data_prevista = now
            data_devolucao = None
            status = "ativo"
            renovacoes = 0

        schema = EmprestimoOut.model_validate(MockEmprestimo())
        assert schema.id == emp_id
        assert schema.exemplar_id == ex_id
        assert schema.leitor_id == lei_id
        assert schema.titulo_obra == "Clean Architecture"
        assert schema.status == "ativo"
        assert schema.renovacoes == 0
        assert schema.data_devolucao is None


class TestEmprestimoListOut:
    def test_valida_lista(self):
        schema = EmprestimoListOut(items=[], total=0, page=1, page_size=20)
        assert schema.items == []
        assert schema.total == 0
        assert schema.page == 1
        assert schema.page_size == 20


class TestConfiguracaoSchemas:
    def test_configuracao_out(self):
        class MockConfig:
            chave = "dias_emprestimo"
            valor = "14"

        schema = ConfiguracaoOut.model_validate(MockConfig())
        assert schema.chave == "dias_emprestimo"
        assert schema.valor == "14"

    def test_configuracao_update_in(self):
        schema = ConfiguracaoUpdateIn(valor="21")
        assert schema.valor == "21"

    def test_configuracao_list_out(self):
        item = ConfiguracaoOut(chave="max_renovacoes", valor="3")
        schema = ConfiguracaoListOut(items=[item])
        assert len(schema.items) == 1
        assert schema.items[0].chave == "max_renovacoes"
