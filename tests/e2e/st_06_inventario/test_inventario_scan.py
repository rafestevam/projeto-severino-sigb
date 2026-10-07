"""
Testes E2E — ST-06 US-019: Inventário por Bipagem de QR Code
Casos: INV-E2E-001 a INV-E2E-012

Estratégia:
  - HTTP real ao ASGI com PostgreSQL de teste via fixture `client`.
  - Setup de estado via fixtures injetadas pelo pytest (obra_factory, exemplar_factory,
    obra_com_exemplar) — nunca via import direto de conftest.
  - Verificações de inventario_log feitas via fixture `db_session` (mesma transação).
  - Sem asserções em helpers/factories: assert pertence ao corpo do teste.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ─── INV-E2E-001 ─────────────────────────────────────────────────────────────

async def test_inv_e2e_001_scan_retorna_200_com_tres_listas(
    client: AsyncClient,
    auth_headers_admin: dict,
    obra_com_exemplar,
):
    """POST /api/inventario/scan retorna 200 com as três listas."""
    obra, exemplar = await obra_com_exemplar("A-01")

    resp = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [exemplar["codigo_qr"]], "localizacao": "A-01"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "encontrados" in data
    assert "nao_bipados" in data
    assert "nao_esperados" in data


# ─── INV-E2E-002 ─────────────────────────────────────────────────────────────

async def test_inv_e2e_002_exemplar_bipado_na_localizacao_correta_aparece_em_encontrados(
    client: AsyncClient,
    auth_headers_admin: dict,
    obra_com_exemplar,
):
    """Exemplar bipado na localização informada aparece em 'encontrados'."""
    obra, exemplar = await obra_com_exemplar("B-01")

    resp = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [exemplar["codigo_qr"]], "localizacao": "B-01"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 200
    qrs_encontrados = [e["codigo_qr"] for e in resp.json()["encontrados"]]
    assert exemplar["codigo_qr"] in qrs_encontrados


# ─── INV-E2E-003 ─────────────────────────────────────────────────────────────

async def test_inv_e2e_003_exemplar_disponivel_nao_bipado_aparece_em_nao_bipados(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_factory,
):
    """Exemplar disponível na localização mas não bipado aparece em 'nao_bipados'."""
    obra = await obra_factory(db_session)
    ex1 = await exemplar_factory(db_session, obra_id=obra.id, localizacao_estante="C-01")
    ex2 = await exemplar_factory(db_session, obra_id=obra.id, localizacao_estante="C-01")

    resp = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [ex1.codigo_qr], "localizacao": "C-01"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 200
    data = resp.json()
    nao_bipados_qrs = [e["codigo_qr"] for e in data["nao_bipados"]]
    encontrados_qrs = [e["codigo_qr"] for e in data["encontrados"]]
    assert ex2.codigo_qr in nao_bipados_qrs
    assert ex1.codigo_qr in encontrados_qrs
    assert ex1.codigo_qr not in nao_bipados_qrs


# ─── INV-E2E-004 ─────────────────────────────────────────────────────────────

async def test_inv_e2e_004_exemplar_emprestado_nao_aparece_em_nao_bipados(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_factory,
    leitor_factory,
    emprestimo_factory,
):
    """Exemplar com estado='emprestado' não aparece em 'nao_bipados'."""
    obra = await obra_factory(db_session)
    leitor = await leitor_factory(db_session)
    ex = await exemplar_factory(
        db_session, obra_id=obra.id, estado="emprestado", localizacao_estante="D-01"
    )
    await emprestimo_factory(db_session, exemplar_id=ex.id, leitor_id=leitor.id, status="ativo")

    resp = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [], "localizacao": "D-01"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 200
    nao_bipados_qrs = [e["codigo_qr"] for e in resp.json()["nao_bipados"]]
    assert ex.codigo_qr not in nao_bipados_qrs


# ─── INV-E2E-005 ─────────────────────────────────────────────────────────────

async def test_inv_e2e_005_exemplar_bipado_de_outra_estante_aparece_em_nao_esperados(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_factory,
):
    """Exemplar bipado cuja localização difere da informada aparece em 'nao_esperados'."""
    obra = await obra_factory(db_session)
    ex = await exemplar_factory(db_session, obra_id=obra.id, localizacao_estante="E-01")

    resp = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [ex.codigo_qr], "localizacao": "F-02"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 200
    data = resp.json()
    nao_esperados_qrs = [e["codigo_qr"] for e in data["nao_esperados"]]
    encontrados_qrs = [e["codigo_qr"] for e in data["encontrados"]]
    assert ex.codigo_qr in nao_esperados_qrs
    assert ex.codigo_qr not in encontrados_qrs


# ─── INV-E2E-006 ─────────────────────────────────────────────────────────────

async def test_inv_e2e_006_scan_gera_registro_em_inventario_log(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_factory,
):
    """Cada QR bipado gera um registro em inventario_log com acao='encontrado'."""
    obra = await obra_factory(db_session)
    ex = await exemplar_factory(db_session, obra_id=obra.id, localizacao_estante="G-01")

    await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [ex.codigo_qr], "localizacao": "G-01"},
        headers=auth_headers_admin,
    )

    result = await db_session.execute(
        text(
            "SELECT COUNT(*) FROM inventario_log "
            "WHERE exemplar_id = :eid AND acao = 'encontrado'"
        ),
        {"eid": ex.id},
    )
    assert result.scalar_one() >= 1


# ─── INV-E2E-007 ─────────────────────────────────────────────────────────────

async def test_inv_e2e_007_qr_desconhecido_ignorado_sem_erro(
    client: AsyncClient,
    auth_headers_admin: dict,
):
    """QR não cadastrado no banco é ignorado silenciosamente (sem 404)."""
    resp = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": ["QR-INEXISTENTE-9999"], "localizacao": "A-01"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["encontrados"] == []
    assert data["nao_esperados"] == []


# ─── INV-E2E-008 ─────────────────────────────────────────────────────────────

async def test_inv_e2e_008_scan_com_lista_vazia_retorna_tres_listas(
    client: AsyncClient,
    auth_headers_admin: dict,
):
    """Scan com lista vazia retorna as três listas (sem erros)."""
    resp = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [], "localizacao": "Z-99"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["encontrados"], list)
    assert isinstance(data["nao_bipados"], list)
    assert isinstance(data["nao_esperados"], list)


# ─── INV-E2E-009 ─────────────────────────────────────────────────────────────

async def test_inv_e2e_009_scan_idempotente_nao_altera_estado_exemplar(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_factory,
):
    """Executar scan duas vezes não altera o estado dos exemplares."""
    obra = await obra_factory(db_session)
    ex = await exemplar_factory(db_session, obra_id=obra.id, localizacao_estante="H-01")
    payload = {"codigos_qr": [ex.codigo_qr], "localizacao": "H-01"}

    resp1 = await client.post("/api/inventario/scan", json=payload, headers=auth_headers_admin)
    resp2 = await client.post("/api/inventario/scan", json=payload, headers=auth_headers_admin)

    assert resp1.status_code == 200
    assert resp2.status_code == 200

    result = await db_session.execute(
        text("SELECT estado FROM exemplar WHERE id = :id"), {"id": ex.id}
    )
    assert result.scalar_one() == "disponivel"


# ─── INV-E2E-010 ─────────────────────────────────────────────────────────────

async def test_inv_e2e_010_itens_contem_codigo_qr_e_estado(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_factory,
):
    """Cada item nas três listas contém 'codigo_qr' e 'estado'."""
    obra = await obra_factory(db_session)
    ex1 = await exemplar_factory(db_session, obra_id=obra.id, localizacao_estante="I-01")
    ex2 = await exemplar_factory(db_session, obra_id=obra.id, localizacao_estante="I-01")
    ex3 = await exemplar_factory(db_session, obra_id=obra.id, localizacao_estante="J-01")

    resp = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [ex1.codigo_qr, ex3.codigo_qr], "localizacao": "I-01"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 200
    data = resp.json()
    for lista in ["encontrados", "nao_bipados", "nao_esperados"]:
        for item in data[lista]:
            assert "codigo_qr" in item
            assert "estado" in item


# ─── INV-E2E-011 ─────────────────────────────────────────────────────────────

async def test_inv_e2e_011_sem_token_retorna_401(client: AsyncClient):
    """Endpoint sem token retorna 401."""
    resp = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [], "localizacao": "A-01"},
    )
    assert resp.status_code == 401


# ─── INV-E2E-012 ─────────────────────────────────────────────────────────────

async def test_inv_e2e_012_token_operador_e_aceito_no_mvp(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """
    No MVP, qualquer token Bearer válido é aceito (role validation pós-MVP via Keycloak).
    O teste documenta o comportamento atual e o esperado após integração de roles.
    """
    resp = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [], "localizacao": "A-01"},
        headers=auth_headers_operador,
    )
    # MVP: 200 (sem validação de role real); pós-MVP: 403
    assert resp.status_code in (200, 403)
