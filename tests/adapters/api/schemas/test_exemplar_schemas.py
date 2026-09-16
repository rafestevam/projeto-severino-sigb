"""
Testes unitários para os schemas Pydantic de exemplar.

Cobre:
  - ExemplarBatchIn: campo quantidade (mínimo 1), localizacao_estante obrigatório.
  - ExemplarOut: construção a partir de atributos (from_attributes), todos os campos.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.adapters.api.schemas.exemplar import ExemplarBatchIn, ExemplarOut


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exemplar_out_obj(**overrides) -> object:
    """Retorna um objeto simples com os atributos esperados por ExemplarOut."""
    class _Obj:
        pass

    attrs = {
        "id": uuid4(),
        "obra_id": uuid4(),
        "codigo_qr": "LIB-2025-00001",
        "estado": "disponivel",
        "localizacao_estante": "A-01",
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
    }
    attrs.update(overrides)
    obj = _Obj()
    for k, v in attrs.items():
        setattr(obj, k, v)
    return obj


# ---------------------------------------------------------------------------
# ExemplarBatchIn — validação
# ---------------------------------------------------------------------------


class TestExemplarBatchIn:
    def test_payload_valido(self):
        """Payload com quantidade=1 e localizacao_estante deve ser aceito."""
        schema = ExemplarBatchIn(quantidade=1, localizacao_estante="A-01")
        assert schema.quantidade == 1
        assert schema.localizacao_estante == "A-01"

    def test_quantidade_multipla(self):
        """Quantidade maior que 1 deve ser aceita sem restrição."""
        schema = ExemplarBatchIn(quantidade=10, localizacao_estante="B-02")
        assert schema.quantidade == 10

    def test_quantidade_zero_rejeitada(self):
        """quantidade=0 deve levantar ValidationError (ge=1)."""
        with pytest.raises(ValidationError):
            ExemplarBatchIn(quantidade=0, localizacao_estante="A-01")

    def test_quantidade_negativa_rejeitada(self):
        """quantidade negativa deve levantar ValidationError."""
        with pytest.raises(ValidationError):
            ExemplarBatchIn(quantidade=-5, localizacao_estante="A-01")

    def test_localizacao_estante_obrigatorio(self):
        """Sem localizacao_estante deve levantar ValidationError."""
        with pytest.raises(ValidationError):
            ExemplarBatchIn(quantidade=1)  # type: ignore[call-arg]

    def test_quantidade_obrigatorio(self):
        """Sem quantidade deve levantar ValidationError."""
        with pytest.raises(ValidationError):
            ExemplarBatchIn(localizacao_estante="A-01")  # type: ignore[call-arg]

    def test_localizacao_estante_aceita_qualquer_string(self):
        """localizacao_estante aceita qualquer string não-vazia."""
        schema = ExemplarBatchIn(quantidade=1, localizacao_estante="Corredor 3, Prateleira B")
        assert schema.localizacao_estante == "Corredor 3, Prateleira B"

    def test_quantidade_grande_e_aceita(self):
        """Quantidade muito grande (ex: 999) deve ser aceita."""
        schema = ExemplarBatchIn(quantidade=999, localizacao_estante="C-99")
        assert schema.quantidade == 999


# ---------------------------------------------------------------------------
# ExemplarOut — serialização e from_attributes
# ---------------------------------------------------------------------------


class TestExemplarOut:
    def test_model_validate_a_partir_de_objeto(self):
        """ExemplarOut.model_validate deve aceitar objeto com atributos (ORM-like)."""
        obj = _exemplar_out_obj()
        schema = ExemplarOut.model_validate(obj)
        assert schema.codigo_qr == "LIB-2025-00001"
        assert schema.estado == "disponivel"

    def test_todos_os_campos_mapeados(self):
        """Todos os campos do objeto devem ser refletidos corretamente no schema."""
        exemplar_id = uuid4()
        obra_id = uuid4()
        created = datetime(2025, 3, 10, tzinfo=timezone.utc)

        obj = _exemplar_out_obj(
            id=exemplar_id,
            obra_id=obra_id,
            codigo_qr="LIB-2025-00042",
            estado="emprestado",
            localizacao_estante="Z-99",
            created_at=created,
        )
        schema = ExemplarOut.model_validate(obj)

        assert schema.id == exemplar_id
        assert schema.obra_id == obra_id
        assert schema.codigo_qr == "LIB-2025-00042"
        assert schema.estado == "emprestado"
        assert schema.localizacao_estante == "Z-99"
        assert schema.created_at == created

    def test_codigo_qr_formato_lib(self):
        """Código QR no formato LIB-{ANO}-{SEQ} deve ser armazenado sem modificação."""
        obj = _exemplar_out_obj(codigo_qr="LIB-2025-00007")
        schema = ExemplarOut.model_validate(obj)
        assert schema.codigo_qr == "LIB-2025-00007"

    def test_estado_disponivel(self):
        """Estado 'disponivel' deve ser serializado corretamente."""
        obj = _exemplar_out_obj(estado="disponivel")
        schema = ExemplarOut.model_validate(obj)
        assert schema.estado == "disponivel"

    def test_estado_emprestado(self):
        """Estado 'emprestado' deve ser serializado corretamente."""
        obj = _exemplar_out_obj(estado="emprestado")
        schema = ExemplarOut.model_validate(obj)
        assert schema.estado == "emprestado"

    def test_ids_sao_uuids(self):
        """Os campos id e obra_id devem ser UUID."""
        from uuid import UUID
        obj = _exemplar_out_obj()
        schema = ExemplarOut.model_validate(obj)
        assert isinstance(schema.id, UUID)
        assert isinstance(schema.obra_id, UUID)

    def test_created_at_e_datetime(self):
        """created_at deve ser um objeto datetime."""
        obj = _exemplar_out_obj()
        schema = ExemplarOut.model_validate(obj)
        assert isinstance(schema.created_at, datetime)
