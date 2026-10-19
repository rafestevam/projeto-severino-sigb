"""
Fixtures e helpers específicos para os testes e2e do ST-08 — OPAC.

Fornece:
  - Reexporta obra_factory, exemplar_factory, leitor_factory e emprestimo_factory
    do conftest do ST-04 (evita duplicação).
  - gerar_cpf_valido(): CPF aleatório com dígitos verificadores corretos. Os CPFs
    do seed_dev.py não passam na validação, então os testes geram os seus.
  - token_leitor(email): JWT não assinado com as claims `email` e `email_verified`,
    usadas por get_leitor_autenticado para resolver o leitor (decisão D1 do ST-08).
    A assinatura ainda não é verificada pela API (enhancement 003).

As fixtures client, db_session e auth_headers_* são herdadas de tests/e2e/conftest.py.
"""

from __future__ import annotations

import base64
import json
import random

from tests.e2e.st_04_circulacao.conftest import (  # noqa: F401 — reexport
    emprestimo_factory,
    exemplar_factory,
    leitor_factory,
    obra_factory,
)


def _digito_verificador(digitos: list[int]) -> int:
    peso_inicial = len(digitos) + 1
    resto = sum(d * (peso_inicial - i) for i, d in enumerate(digitos)) % 11
    return 0 if resto < 2 else 11 - resto


def gerar_cpf_valido(*, mascarado: bool = False) -> str:
    base = [random.randint(0, 9) for _ in range(9)]
    while len(set(base)) == 1:
        base = [random.randint(0, 9) for _ in range(9)]
    base.append(_digito_verificador(base))
    base.append(_digito_verificador(base))
    digitos = "".join(map(str, base))
    if mascarado:
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
    return digitos


def mascarar_cpf(digitos: str) -> str:
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def token_leitor(email: str, *, email_verified: bool = True) -> dict[str, str]:
    claims = {
        "sub": "leitor-e2e",
        "email": email,
        "email_verified": email_verified,
        "realm_access": {"roles": ["leitor"]},
    }
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return {"Authorization": f"Bearer eyJhbGciOiJub25lIn0.{payload}."}
