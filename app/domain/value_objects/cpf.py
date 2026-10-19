from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.domain.exceptions import CpfInvalidoError

_TAMANHO_CPF = 11


def normalizar_cpf(texto: str) -> str:
    """Remove a máscara (pontos, traço, espaços) e devolve apenas os dígitos."""
    return re.sub(r"\D", "", texto)


def hash_cpf(texto: str) -> str:
    """SHA-256 dos dígitos do CPF, para que entradas com e sem máscara colidam."""
    return hashlib.sha256(normalizar_cpf(texto).encode()).hexdigest()


def _digito_verificador(digitos: str) -> int:
    peso_inicial = len(digitos) + 1
    soma = sum(int(d) * (peso_inicial - i) for i, d in enumerate(digitos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


@dataclass(frozen=True, slots=True)
class Cpf:
    """CPF validado (11 dígitos e dígitos verificadores conferidos)."""

    digitos: str

    @classmethod
    def de(cls, texto: str) -> Cpf:
        digitos = normalizar_cpf(texto)
        if len(digitos) != _TAMANHO_CPF or len(set(digitos)) == 1:
            raise CpfInvalidoError()
        primeiro = _digito_verificador(digitos[:9])
        segundo = _digito_verificador(digitos[:10])
        if digitos[9:] != f"{primeiro}{segundo}":
            raise CpfInvalidoError()
        return cls(digitos)

    def hash(self) -> str:
        return hash_cpf(self.digitos)
