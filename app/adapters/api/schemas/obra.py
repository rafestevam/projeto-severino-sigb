from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class ObraIn(BaseModel):
    isbn: str | None = None
    titulo: str
    autores: list[str]
    editora: str
    ano: int
    capa_url: str | None = None
    categoria: str

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
    created_at: datetime


class ObraListOut(BaseModel):
    items: list[ObraOut]
    total: int
    page: int
    page_size: int
