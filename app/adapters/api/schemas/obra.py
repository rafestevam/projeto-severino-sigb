from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.use_cases.listar_catalogo_publico import ItemCatalogo, PaginaCatalogo
from app.use_cases.obter_obra_publica import DetalheObraPublica


class ObraIn(BaseModel):
    isbn: str | None = None
    titulo: str
    autores: list[str]
    editora: str
    ano: int
    capa_url: str | None = None
    categoria: str
    sinopse: str | None = None

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, value: str | None) -> str | None:
        if value is None:
            return None

        isbn = value.replace("-", "").replace(" ", "")
        if len(isbn) == 13 and isbn.isdigit():
            check_digit = sum(
                int(digit) * (1 if index % 2 == 0 else 3)
                for index, digit in enumerate(isbn[:12])
            )
            if (10 - check_digit % 10) % 10 == int(isbn[-1]):
                return value
        elif len(isbn) == 10 and isbn[:-1].isdigit():
            weighted_sum = sum(
                int(digit) * (10 - index) for index, digit in enumerate(isbn[:9])
            )
            check_value = 10 if isbn[-1].upper() == "X" else int(isbn[-1]) if isbn[-1].isdigit() else -1
            if check_value >= 0 and (weighted_sum + check_value) % 11 == 0:
                return value

        raise ValueError("ISBN inválido")


class ObraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    isbn: str | None
    titulo: str
    autores: list[str]
    editora: str
    ano: int
    capa_url: str | None
    categoria: str
    sinopse: str | None = None
    created_at: datetime


class ObraListOut(BaseModel):
    items: list[ObraOut]
    total: int
    page: int
    page_size: int


class ObraPublicaOut(BaseModel):
    """Card do OPAC: só campos não sensíveis e disponibilidade agregada."""

    id: UUID
    titulo: str
    autores: list[str]
    capa_url: str | None
    categoria: str
    disponivel: bool

    @classmethod
    def de_item(cls, item: ItemCatalogo) -> ObraPublicaOut:
        obra = item.obra
        return cls(
            id=obra.id,
            titulo=obra.titulo,
            autores=obra.autores,
            capa_url=obra.capa_url,
            categoria=obra.categoria,
            disponivel=item.disponibilidade.disponivel,
        )


class ObraPublicaListOut(BaseModel):
    items: list[ObraPublicaOut]
    total: int
    page: int
    page_size: int

    @classmethod
    def de_pagina(cls, pagina: PaginaCatalogo) -> ObraPublicaListOut:
        return cls(
            items=[ObraPublicaOut.de_item(item) for item in pagina.itens],
            total=pagina.total,
            page=pagina.page,
            page_size=pagina.page_size,
        )


class ObraPublicaDetalheOut(ObraPublicaOut):
    editora: str
    ano: int
    sinopse: str | None
    exemplares_disponiveis: int
    exemplares_emprestados: int
    posicao_ranking: int | None

    @classmethod
    def de_detalhe(cls, detalhe: DetalheObraPublica) -> ObraPublicaDetalheOut:
        obra = detalhe.obra
        disponibilidade = detalhe.disponibilidade
        return cls(
            id=obra.id,
            titulo=obra.titulo,
            autores=obra.autores,
            capa_url=obra.capa_url,
            categoria=obra.categoria,
            disponivel=disponibilidade.disponivel,
            editora=obra.editora,
            ano=obra.ano,
            sinopse=obra.sinopse,
            exemplares_disponiveis=disponibilidade.disponiveis,
            exemplares_emprestados=disponibilidade.emprestados,
            posicao_ranking=detalhe.posicao_ranking,
        )
