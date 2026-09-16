"""
Testes e2e — Fluxo Completo de Catalogação (Happy Path)
Sub-Tarefa 6 do plano ST-03.

Cobre o caso FLOW-001.

Este teste valida a interoperabilidade entre US-008, US-009 e US-010 como um
fluxo de trabalho único percorrendo toda a jornada do operador:

  Passo 1: Buscar metadados por ISBN  (US-008)
  Passo 2: Cadastrar obra com esses metadados  (US-009)
  Passo 3: Criar 2 exemplares da obra  (US-010)
  Passo 4: Gerar etiqueta PDF do primeiro exemplar  (US-010)

A saída de cada passo alimenta o próximo — o teste falha na primeira etapa
com problema se o fluxo quebrar em qualquer ponto.

Marcado com xfail até que todos os endpoints de catalogação sejam implementados.
"""

from __future__ import annotations

import re

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# ISBN que o FakeIsbnGateway resolve com metadados completos
ISBN_FLOW = "9788535902778"

# Padrão esperado para códigos QR
CODIGO_QR_PATTERN = re.compile(r"^LIB-\d{4}-\d{5}$")


# ─── FLOW-001: Fluxo completo de catalogação ──────────────────────────────────

@pytest.mark.xfail(
    reason="Endpoints de catalogação (US-008, US-009, US-010) não implementados",
    strict=False,
)
async def test_flow_001_fluxo_completo_catalogacao(
    client: AsyncClient,
    auth_headers_operador: dict,
    isbn_gateway_override,
):
    """
    FLOW-001 — Fluxo completo: busca ISBN → cadastra obra → cria 2 exemplares → gera etiqueta.
    Histórias vinculadas: US-008 + US-009 + US-010.

    Cada passo usa os dados retornados pelo passo anterior.
    """

    # ── Passo 1: Buscar metadados por ISBN (US-008) ───────────────────────────
    resp_isbn = await client.post(
        f"/api/obras/isbn/{ISBN_FLOW}",
        headers=auth_headers_operador,
    )
    assert resp_isbn.status_code == 200, (
        f"Passo 1 falhou: POST /api/obras/isbn/{ISBN_FLOW} retornou {resp_isbn.status_code}"
    )
    metadados = resp_isbn.json()
    assert metadados.get("titulo") is not None, (
        "Passo 1 falhou: FakeIsbnGateway deveria retornar titulo não nulo para este ISBN"
    )

    # ── Passo 2: Cadastrar obra com os metadados obtidos (US-009) ─────────────
    payload_obra = {
        "isbn": ISBN_FLOW,
        "titulo": metadados["titulo"],
        "autores": metadados.get("autores") or ["Autor Desconhecido"],
        "editora": metadados.get("editora") or "Editora Desconhecida",
        "ano": metadados.get("ano") or 2024,
        "capa_url": metadados.get("capa_url"),
        "categoria": "Literatura Brasileira",
    }

    resp_obra = await client.post(
        "/api/obras",
        json=payload_obra,
        headers=auth_headers_operador,
    )
    assert resp_obra.status_code == 201, (
        f"Passo 2 falhou: POST /api/obras retornou {resp_obra.status_code} — "
        f"body: {resp_obra.text}"
    )
    obra_data = resp_obra.json()
    obra_id = obra_data["id"]
    assert obra_id is not None, "Passo 2 falhou: obra criada sem id"

    # ── Passo 3: Criar 2 exemplares da obra (US-010) ──────────────────────────
    resp_exemplares = await client.post(
        f"/api/obras/{obra_id}/exemplares",
        json={"quantidade": 2, "localizacao_estante": "A-01"},
        headers=auth_headers_operador,
    )
    assert resp_exemplares.status_code == 201, (
        f"Passo 3 falhou: POST /api/obras/{obra_id}/exemplares retornou "
        f"{resp_exemplares.status_code} — body: {resp_exemplares.text}"
    )
    exemplares = resp_exemplares.json()
    assert len(exemplares) == 2, (
        f"Passo 3 falhou: esperados 2 exemplares, recebidos {len(exemplares)}"
    )

    # Valida formato dos códigos QR
    for exemplar in exemplares:
        codigo_qr = exemplar["codigo_qr"]
        assert CODIGO_QR_PATTERN.match(codigo_qr), (
            f"Passo 3 falhou: codigo_qr '{codigo_qr}' não segue formato LIB-YYYY-NNNNN"
        )

    primeiro_codigo_qr = exemplares[0]["codigo_qr"]

    # ── Passo 4: Gerar etiqueta PDF do primeiro exemplar (US-010) ────────────
    resp_etiqueta = await client.get(
        f"/api/exemplares/{primeiro_codigo_qr}/etiqueta.pdf",
        headers=auth_headers_operador,
    )
    assert resp_etiqueta.status_code == 200, (
        f"Passo 4 falhou: GET /api/exemplares/{primeiro_codigo_qr}/etiqueta.pdf "
        f"retornou {resp_etiqueta.status_code}"
    )
    assert "application/pdf" in resp_etiqueta.headers.get("content-type", ""), (
        "Passo 4 falhou: Content-Type não é application/pdf"
    )
    assert resp_etiqueta.content[:4] == b"%PDF", (
        f"Passo 4 falhou: resposta não começa com %PDF: {resp_etiqueta.content[:16]!r}"
    )
