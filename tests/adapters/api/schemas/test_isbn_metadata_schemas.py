"""
Testes unitários para o schema Pydantic IsbnMetadataOut.

Cobre:
  - Todos os campos são opcionais e default a None.
  - Campos preenchidos são preservados sem modificação.
  - Construção parcial (apenas alguns campos) é válida.
  - Serialização via model_dump.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.adapters.api.schemas.isbn_metadata import IsbnMetadataOut


# ---------------------------------------------------------------------------
# Testes — campos opcionais e defaults
# ---------------------------------------------------------------------------


class TestIsbnMetadataOut:
    def test_instancia_vazia_com_todos_none(self):
        """IsbnMetadataOut() sem argumentos deve ter todos os campos None."""
        schema = IsbnMetadataOut()
        assert schema.titulo is None
        assert schema.autores is None
        assert schema.editora is None
        assert schema.ano is None
        assert schema.capa_url is None

    def test_todos_os_campos_opcionais(self):
        """Deve ser possível construir IsbnMetadataOut sem nenhum argumento."""
        # Não deve levantar ValidationError
        schema = IsbnMetadataOut()
        assert schema is not None

    def test_todos_os_campos_preenchidos(self):
        """Todos os campos preenchidos devem ser armazenados sem modificação."""
        schema = IsbnMetadataOut(
            titulo="Dom Casmurro",
            autores=["Machado de Assis"],
            editora="Ática",
            ano=1899,
            capa_url="https://example.com/capa.jpg",
        )
        assert schema.titulo == "Dom Casmurro"
        assert schema.autores == ["Machado de Assis"]
        assert schema.editora == "Ática"
        assert schema.ano == 1899
        assert schema.capa_url == "https://example.com/capa.jpg"

    def test_apenas_titulo_preenchido(self):
        """Schema com apenas título deve ter os demais campos None."""
        schema = IsbnMetadataOut(titulo="Apenas Título")
        assert schema.titulo == "Apenas Título"
        assert schema.autores is None
        assert schema.editora is None
        assert schema.ano is None
        assert schema.capa_url is None

    def test_apenas_autores_preenchidos(self):
        """Schema com apenas autores deve ter os demais campos None."""
        schema = IsbnMetadataOut(autores=["Autor A", "Autor B"])
        assert schema.titulo is None
        assert schema.autores == ["Autor A", "Autor B"]

    def test_apenas_editora_preenchida(self):
        """Schema com apenas editora deve ter os demais campos None."""
        schema = IsbnMetadataOut(editora="Minha Editora")
        assert schema.editora == "Minha Editora"
        assert schema.titulo is None

    def test_apenas_ano_preenchido(self):
        """Schema com apenas ano deve ter os demais campos None."""
        schema = IsbnMetadataOut(ano=2024)
        assert schema.ano == 2024
        assert schema.titulo is None

    def test_apenas_capa_url_preenchida(self):
        """Schema com apenas capa_url deve ter os demais campos None."""
        schema = IsbnMetadataOut(capa_url="https://example.com/capa.jpg")
        assert schema.capa_url == "https://example.com/capa.jpg"
        assert schema.titulo is None

    def test_autores_lista_vazia_vs_none(self):
        """Lista vazia de autores é diferente de None."""
        schema_none = IsbnMetadataOut(autores=None)
        schema_vazia = IsbnMetadataOut(autores=[])
        assert schema_none.autores is None
        assert schema_vazia.autores == []

    def test_multiplos_autores(self):
        """Lista com múltiplos autores deve ser preservada."""
        schema = IsbnMetadataOut(autores=["A", "B", "C"])
        assert schema.autores == ["A", "B", "C"]

    def test_ano_inteiro(self):
        """Ano deve ser armazenado como inteiro."""
        schema = IsbnMetadataOut(ano=2008)
        assert isinstance(schema.ano, int)
        assert schema.ano == 2008


# ---------------------------------------------------------------------------
# Testes — serialização model_dump
# ---------------------------------------------------------------------------


class TestIsbnMetadataOutSerializacao:
    def test_model_dump_schema_vazio(self):
        """model_dump de schema vazio deve retornar dict com todos os valores None."""
        schema = IsbnMetadataOut()
        data = schema.model_dump()
        assert data["titulo"] is None
        assert data["autores"] is None
        assert data["editora"] is None
        assert data["ano"] is None
        assert data["capa_url"] is None

    def test_model_dump_schema_preenchido(self):
        """model_dump deve refletir os campos preenchidos corretamente."""
        schema = IsbnMetadataOut(titulo="Dom Casmurro", ano=1899)
        data = schema.model_dump()
        assert data["titulo"] == "Dom Casmurro"
        assert data["ano"] == 1899
        assert data["autores"] is None

    def test_campos_presentes_mesmo_com_none(self):
        """Todos os campos devem estar presentes no dict mesmo quando None."""
        schema = IsbnMetadataOut()
        data = schema.model_dump()
        expected_keys = {"titulo", "autores", "editora", "ano", "capa_url"}
        assert expected_keys.issubset(data.keys())
