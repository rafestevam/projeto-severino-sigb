from __future__ import annotations

from pydantic import BaseModel


class InventarioScanIn(BaseModel):
    codigos_qr: list[str]
    localizacao: str


class ExemplarScanOut(BaseModel):
    codigo_qr: str
    estado: str


class InventarioScanOut(BaseModel):
    encontrados: list[ExemplarScanOut]
    nao_bipados: list[ExemplarScanOut]
    nao_esperados: list[ExemplarScanOut]
