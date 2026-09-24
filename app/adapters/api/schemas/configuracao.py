from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ConfiguracaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chave: str
    valor: str


class ConfiguracaoUpdateIn(BaseModel):
    valor: str


class ConfiguracaoListOut(BaseModel):
    items: list[ConfiguracaoOut]
