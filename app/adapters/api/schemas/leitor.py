from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator


class LeitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    ativo: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status(self) -> Literal["ativo", "pendente"]:
        return "ativo" if self.ativo else "pendente"


class LeitorPreCadastroIn(BaseModel):
    nome: str = Field(min_length=3, max_length=256)
    cpf: str = Field(min_length=11, max_length=14)
    telefone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = Field(default=None, max_length=256)

    @field_validator("telefone", "email", mode="before")
    @classmethod
    def vazio_vira_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class LeitorPreCadastroOut(BaseModel):
    """Resposta deliberadamente mínima: não devolve id nem CPF ao visitante."""

    status: Literal["pendente"] = "pendente"
