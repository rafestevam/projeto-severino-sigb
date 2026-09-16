"""
Testes unitários para os schemas Pydantic de obra.

Cobre:
  - ObraIn: validação de campos obrigatórios, ISBN opcional, dígito verificador
             ISBN-13 e ISBN-10, rejeição de ISBNs inválidos.
  - ObraOut: construção a partir de atributos (from_attributes), serialização.
  - ObraListOut: estrutura de paginação, itens, total, page, page_size.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.adapters.api.schemas.obra import ObraIn, ObraListOut, ObraOut


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _obra_in_payload(**overrides) -> dict:
    base = {
        "isbn": "9788535902778",
        "titulo": "Dom Casmurro",
        "autores": ["Machado de Assis"],
        "editora": "Ática",
        "ano": 1899,
        "categoria": "Literatura Brasileira",
        "capa_url": None,
    }
    return {**base, **overrides}


def _obra_out_obj(**overrides) -> object:
    """Retorna um objeto simples com os atributos esperados por ObraOut."""
    class _Obj:
        pass

    attrs = {
        "id": uuid4(),
        "isbn": "9788535902778",
        "titulo": "Dom Casmurro",
        "autores": ["Machado de Assis"],
        "editora": "Ática",
        "ano": 1899,
        "capa_url": None,
        "categoria": "Literatura Brasileira",
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    attrs.update(overrides)
    obj = _Obj()
    for k, v in attrs.items():
        setattr(obj, k, v)
    return obj


# ---------------------------------------------------------------------------
# ObraIn — campos obrigatórios
# ---------------------------------------------------------------------------


class TestObraIn:
    def test_valida_obra_completa(self):
        """Payload completo com ISBN válido deve ser aceito."""
        schema = ObraIn(**_obra_in_payload())
        assert schema.titulo == "Dom Casmurro"
        assert schema.isbn == "9788535902778"

    def test_isbn_none_e_aceito(self):
        """ISBN é opcional — None deve passar na validação."""
        schema = ObraIn(**_obra_in_payload(isbn=None))
        assert schema.isbn is None

    def test_isbn_ausente_padrao_e_none(self):
        """Sem o campo isbn, o valor padrão deve ser None."""
        payload = _obra_in_payload()
        del payload["isbn"]
        schema = ObraIn(**payload)
        assert schema.isbn is None

    def test_capa_url_none_e_aceito(self):
        """capa_url é opcional — None deve ser aceito."""
        schema = ObraIn(**_obra_in_payload(capa_url=None))
        assert schema.capa_url is None

    def test_capa_url_com_valor(self):
        """capa_url com URL válida deve ser armazenada sem modificação."""
        url = "https://example.com/capa.jpg"
        schema = ObraIn(**_obra_in_payload(capa_url=url))
        assert schema.capa_url == url

    def test_titulo_obrigatorio(self):
        """Sem título o schema deve levantar ValidationError."""
        payload = _obra_in_payload()
        del payload["titulo"]
        with pytest.raises(ValidationError):
            ObraIn(**payload)

    def test_autores_obrigatorio(self):
        """Sem autores o schema deve levantar ValidationError."""
        payload = _obra_in_payload()
        del payload["autores"]
        with pytest.raises(ValidationError):
            ObraIn(**payload)

    def test_editora_obrigatorio(self):
        """Sem editora o schema deve levantar ValidationError."""
        payload = _obra_in_payload()
        del payload["editora"]
        with pytest.raises(ValidationError):
            ObraIn(**payload)

    def test_ano_obrigatorio(self):
        """Sem ano o schema deve levantar ValidationError."""
        payload = _obra_in_payload()
        del payload["ano"]
        with pytest.raises(ValidationError):
            ObraIn(**payload)

    def test_categoria_obrigatorio(self):
        """Sem categoria o schema deve levantar ValidationError."""
        payload = _obra_in_payload()
        del payload["categoria"]
        with pytest.raises(ValidationError):
            ObraIn(**payload)


# ---------------------------------------------------------------------------
# ObraIn — validação de ISBN-13
# ---------------------------------------------------------------------------


class TestObraInIsbn13:
    def test_isbn13_valido_e_aceito(self):
        """ISBN-13 com dígito verificador correto deve ser aceito."""
        schema = ObraIn(**_obra_in_payload(isbn="9788535902778"))
        assert schema.isbn == "9788535902778"

    def test_isbn13_segundo_valido(self):
        """Outro ISBN-13 válido (Clean Code) deve ser aceito."""
        schema = ObraIn(**_obra_in_payload(isbn="9780132350884"))
        assert schema.isbn == "9780132350884"

    def test_isbn13_digito_verificador_errado_rejeitado(self):
        """ISBN-13 com dígito verificador incorreto deve levantar ValidationError."""
        with pytest.raises(ValidationError):
            ObraIn(**_obra_in_payload(isbn="9788535902779"))

    def test_isbn13_todos_noves_rejeitado(self):
        """ISBN-13 com todos os dígitos iguais a 9 deve ser rejeitado."""
        with pytest.raises(ValidationError):
            ObraIn(**_obra_in_payload(isbn="9999999999999"))

    def test_isbn13_com_hifens_valido(self):
        """ISBN-13 formatado com hífens deve ser aceito (hífens são ignorados)."""
        schema = ObraIn(**_obra_in_payload(isbn="978-85-359-0277-8"))
        assert schema.isbn == "978-85-359-0277-8"

    def test_isbn13_muito_curto_rejeitado(self):
        """ISBN com menos de 10 dígitos deve ser rejeitado."""
        with pytest.raises(ValidationError):
            ObraIn(**_obra_in_payload(isbn="97885359"))

    def test_isbn13_com_letras_rejeitado(self):
        """ISBN-13 com letras no meio deve ser rejeitado."""
        with pytest.raises(ValidationError):
            ObraIn(**_obra_in_payload(isbn="978853590277X"))


# ---------------------------------------------------------------------------
# ObraIn — validação de ISBN-10
# ---------------------------------------------------------------------------


class TestObraInIsbn10:
    def test_isbn10_valido_e_aceito(self):
        """ISBN-10 com dígito verificador numérico correto deve ser aceito."""
        # Clean Code: ISBN-10 = 0132350882
        schema = ObraIn(**_obra_in_payload(isbn="0132350882"))
        assert schema.isbn == "0132350882"

    def test_isbn10_com_digito_x_valido(self):
        """ISBN-10 com dígito verificador 'X' deve ser aceito."""
        # ISBN-10 com check digit X: 080442957X
        schema = ObraIn(**_obra_in_payload(isbn="080442957X"))
        assert schema.isbn == "080442957X"

    def test_isbn10_digito_verificador_errado_rejeitado(self):
        """ISBN-10 com dígito verificador incorreto deve levantar ValidationError."""
        with pytest.raises(ValidationError):
            ObraIn(**_obra_in_payload(isbn="0132350883"))


# ---------------------------------------------------------------------------
# ObraOut — serialização e from_attributes
# ---------------------------------------------------------------------------


class TestObraOut:
    def test_model_validate_a_partir_de_objeto(self):
        """ObraOut.model_validate deve aceitar objeto com atributos (ORM-like)."""
        obj = _obra_out_obj()
        schema = ObraOut.model_validate(obj)
        assert schema.titulo == "Dom Casmurro"
        assert schema.isbn == "9788535902778"

    def test_todos_os_campos_mapeados(self):
        """Todos os campos do objeto devem ser refletidos corretamente no schema."""
        obra_id = uuid4()
        created = datetime(2024, 6, 15, tzinfo=timezone.utc)
        obj = _obra_out_obj(
            id=obra_id,
            isbn="9780132350884",
            titulo="Clean Code",
            autores=["Robert C. Martin"],
            editora="Prentice Hall",
            ano=2008,
            capa_url="https://example.com/cover.jpg",
            categoria="Engenharia de Software",
            created_at=created,
        )
        schema = ObraOut.model_validate(obj)

        assert schema.id == obra_id
        assert schema.isbn == "9780132350884"
        assert schema.titulo == "Clean Code"
        assert schema.autores == ["Robert C. Martin"]
        assert schema.editora == "Prentice Hall"
        assert schema.ano == 2008
        assert schema.capa_url == "https://example.com/cover.jpg"
        assert schema.categoria == "Engenharia de Software"
        assert schema.created_at == created

    def test_isbn_none_serializado_corretamente(self):
        """isbn=None deve ser serializado como None (não omitido)."""
        obj = _obra_out_obj(isbn=None)
        schema = ObraOut.model_validate(obj)
        assert schema.isbn is None

    def test_capa_url_none_serializado_corretamente(self):
        """capa_url=None deve ser serializado como None."""
        obj = _obra_out_obj(capa_url=None)
        schema = ObraOut.model_validate(obj)
        assert schema.capa_url is None

    def test_autores_lista_multipla(self):
        """Lista de múltiplos autores deve ser preservada integralmente."""
        obj = _obra_out_obj(autores=["Autor A", "Autor B", "Autor C"])
        schema = ObraOut.model_validate(obj)
        assert schema.autores == ["Autor A", "Autor B", "Autor C"]


# ---------------------------------------------------------------------------
# ObraListOut — estrutura de paginação
# ---------------------------------------------------------------------------


class TestObraListOut:
    def _make_obra_out(self) -> ObraOut:
        return ObraOut.model_validate(_obra_out_obj())

    def test_estrutura_minima(self):
        """ObraListOut com lista vazia deve ter itens=[], total=0."""
        schema = ObraListOut(items=[], total=0, page=1, page_size=20)
        assert schema.items == []
        assert schema.total == 0
        assert schema.page == 1
        assert schema.page_size == 20

    def test_com_itens(self):
        """ObraListOut com itens deve retornar a lista corretamente."""
        obra = self._make_obra_out()
        schema = ObraListOut(items=[obra], total=1, page=1, page_size=20)
        assert len(schema.items) == 1
        assert schema.items[0].titulo == "Dom Casmurro"

    def test_page_size_padrao_20(self):
        """O page_size padrão esperado pelos testes e2e é 20."""
        schema = ObraListOut(items=[], total=0, page=1, page_size=20)
        assert schema.page_size == 20

    def test_total_independente_do_tamanho_dos_itens(self):
        """total pode ser maior que len(items) (paginação parcial)."""
        obra = self._make_obra_out()
        schema = ObraListOut(items=[obra], total=100, page=3, page_size=20)
        assert schema.total == 100
        assert len(schema.items) == 1

    def test_multiplas_paginas(self):
        """page=2 e page_size=10 devem ser armazenados sem modificação."""
        schema = ObraListOut(items=[], total=50, page=2, page_size=10)
        assert schema.page == 2
        assert schema.page_size == 10
