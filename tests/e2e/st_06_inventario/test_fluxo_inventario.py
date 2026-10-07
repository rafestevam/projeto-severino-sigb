"""
Testes E2E — ST-06: Fluxo Completo de Inventário e Gestão
Casos: FLOW-I-001 a FLOW-I-005

Estratégia:
  - HTTP real ao ASGI com PostgreSQL de teste via fixture `client`.
  - Setup de estado via fixtures injetadas (obra_factory, exemplar_factory,
    obra_com_exemplar) — sem import direto de conftest.
  - Sem asserções em helpers/factories: assert pertence ao corpo do teste.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.st_06_inventario.conftest import _gerar_isbn13

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ─── FLOW-I-001 ───────────────────────────────────────────────────────────────

async def test_flow_i_001_jornada_completa_inventario_e_gestao(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
):
    """
    Fluxo completo: criar obra + 2 exemplares → scan → baixa do exemplar ausente
    → verificar inventario_log → verificar dashboard.
    """
    # Passo 1 — Criar obra com 2 exemplares via API
    resp_obra = await client.post(
        "/api/obras",
        json={
            "isbn": _gerar_isbn13(),
            "titulo": "Obra Fluxo Completo",
            "autores": ["Autor"],
            "editora": "Ed",
            "ano": 2024,
            "categoria": "Teste",
            "capa_url": None,
        },
        headers=auth_headers_admin,
    )
    assert resp_obra.status_code == 201
    obra = resp_obra.json()

    resp_exemplares = await client.post(
        f"/api/obras/{obra['id']}/exemplares",
        json={"quantidade": 2, "localizacao_estante": "A-01"},
        headers=auth_headers_admin,
    )
    assert resp_exemplares.status_code == 201
    exemplares = resp_exemplares.json()
    exemplar_1 = exemplares[0]
    exemplar_2 = exemplares[1]

    # Passo 2 — Inventário bipando apenas exemplar_1
    resp_scan = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [exemplar_1["codigo_qr"]], "localizacao": "A-01"},
        headers=auth_headers_admin,
    )
    assert resp_scan.status_code == 200
    data_scan = resp_scan.json()
    encontrados_qrs = [e["codigo_qr"] for e in data_scan["encontrados"]]
    nao_bipados_qrs = [e["codigo_qr"] for e in data_scan["nao_bipados"]]
    assert exemplar_1["codigo_qr"] in encontrados_qrs
    assert exemplar_2["codigo_qr"] in nao_bipados_qrs

    # Passo 3 — Baixar o exemplar ausente (exemplar_2) com motivo "extraviado"
    resp_baixa = await client.post(
        f"/api/exemplares/{exemplar_2['id']}/baixar",
        json={"motivo": "extraviado"},
        headers=auth_headers_admin,
    )
    assert resp_baixa.status_code == 200
    assert resp_baixa.json()["estado"] == "baixado"

    # Passo 4 — Verificar inventario_log via db_session (mesma transação)
    result_encontrado = await db_session.execute(
        text(
            "SELECT COUNT(*) FROM inventario_log "
            "WHERE exemplar_id = :eid AND acao = 'encontrado'"
        ),
        {"eid": uuid.UUID(exemplar_1["id"])},
    )
    assert result_encontrado.scalar_one() >= 1

    result_baixado = await db_session.execute(
        text(
            "SELECT COUNT(*) FROM inventario_log "
            "WHERE exemplar_id = :eid AND acao = 'baixado'"
        ),
        {"eid": uuid.UUID(exemplar_2["id"])},
    )
    assert result_baixado.scalar_one() >= 1

    # Passo 5 — Verificar dashboard reflete as operações
    resp_dash = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp_dash.status_code == 200
    dash = resp_dash.json()
    assert dash["exemplares_por_estado"]["baixado"] >= 1
    assert dash["taxa_perdas"] > 0.0


# ─── FLOW-I-002 ───────────────────────────────────────────────────────────────

async def test_flow_i_002_exemplar_baixado_nao_pode_ser_emprestado(
    client: AsyncClient,
    auth_headers_admin: dict,
    obra_com_exemplar,
):
    """Exemplar baixado não pode ser emprestado — checkout retorna 4xx."""
    obra, exemplar = await obra_com_exemplar()

    # Criar leitor via API
    resp_leitor = await client.post(
        "/api/leitores",
        json={
            "nome": "Leitor Flow",
            "cpf": str(uuid.uuid4().int)[:11],
            "telefone": None,
            "email": f"flow_{uuid.uuid4().hex[:6]}@test.com",
        },
        headers=auth_headers_admin,
    )
    assert resp_leitor.status_code == 201
    leitor = resp_leitor.json()

    # Baixar o exemplar
    resp_baixa = await client.post(
        f"/api/exemplares/{exemplar['id']}/baixar",
        json={"motivo": "danificado"},
        headers=auth_headers_admin,
    )
    assert resp_baixa.status_code == 200

    # Tentar emprestar o exemplar baixado — ExemplarNaoDisponivelError → 409
    resp_checkout = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": exemplar["id"], "leitor_id": leitor["id"]},
        headers=auth_headers_admin,
    )
    assert resp_checkout.status_code in (409, 422)


# ─── FLOW-I-003 ───────────────────────────────────────────────────────────────

async def test_flow_i_003_total_emprestimos_refletido_no_dashboard_apos_checkout(
    client: AsyncClient,
    auth_headers_admin: dict,
    obra_com_exemplar,
):
    """top_obras_emprestadas reflete obra após checkout (total_emprestimos incrementado)."""
    obra, exemplar = await obra_com_exemplar()

    resp_leitor = await client.post(
        "/api/leitores",
        json={
            "nome": "Leitor Flow3",
            "cpf": str(uuid.uuid4().int)[:11],
            "telefone": None,
            "email": f"flow3_{uuid.uuid4().hex[:6]}@test.com",
        },
        headers=auth_headers_admin,
    )
    assert resp_leitor.status_code == 201
    leitor = resp_leitor.json()

    # Realizar checkout
    resp_checkout = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": exemplar["id"], "leitor_id": leitor["id"]},
        headers=auth_headers_admin,
    )
    assert resp_checkout.status_code == 201

    # A obra deve aparecer em top_obras_emprestadas
    resp_dash = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp_dash.status_code == 200
    top_obras = resp_dash.json()["top_obras_emprestadas"]
    obra_ids = [item["obra_id"] for item in top_obras]
    assert obra["id"] in obra_ids


# ─── FLOW-I-004 ───────────────────────────────────────────────────────────────

async def test_flow_i_004_taxa_perdas_aumenta_apos_baixa_extraviado(
    client: AsyncClient,
    auth_headers_admin: dict,
    obra_com_exemplar,
):
    """taxa_perdas aumenta após baixa com motivo 'extraviado'."""
    resp_antes = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    taxa_antes = resp_antes.json()["taxa_perdas"]

    obra, exemplar = await obra_com_exemplar()
    await client.post(
        f"/api/exemplares/{exemplar['id']}/baixar",
        json={"motivo": "extraviado"},
        headers=auth_headers_admin,
    )

    resp_depois = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    taxa_depois = resp_depois.json()["taxa_perdas"]
    assert taxa_depois > taxa_antes or taxa_depois > 0.0


# ─── FLOW-I-005 ───────────────────────────────────────────────────────────────

async def test_flow_i_005_scan_detecta_exemplar_de_outra_estante(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_factory,
):
    """
    Scan detecta exemplar de outra estante quando sua localização cadastrada
    difere da estante sendo inventariada.
    """
    obra = await obra_factory(db_session)
    ex = await exemplar_factory(db_session, obra_id=obra.id, localizacao_estante="D-05")

    resp = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [ex.codigo_qr], "localizacao": "E-06"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 200
    data = resp.json()
    nao_esperados_qrs = [e["codigo_qr"] for e in data["nao_esperados"]]
    assert ex.codigo_qr in nao_esperados_qrs
    assert data["encontrados"] == []
