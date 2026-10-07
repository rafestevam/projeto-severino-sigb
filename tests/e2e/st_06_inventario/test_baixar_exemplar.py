"""
Testes E2E — ST-06 US-020: Dar Baixa em Exemplar
Casos: BAI-E2E-001 a BAI-E2E-015

Estratégia:
  - HTTP real ao ASGI com PostgreSQL de teste via fixture `client`.
  - Setup de estado via fixtures injetadas (obra_factory, exemplar_factory,
    exemplar_baixado_factory, obra_com_exemplar) — sem import direto de conftest.
  - Verificações de inventario_log e motivo_baixa via fixture `db_session`.
  - Sem asserções em helpers/factories: assert pertence ao corpo do teste.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ─── BAI-E2E-001 ─────────────────────────────────────────────────────────────

async def test_bai_e2e_001_baixar_retorna_200(
    client: AsyncClient,
    auth_headers_admin: dict,
    obra_com_exemplar,
):
    """POST /api/exemplares/{id}/baixar com motivo válido retorna 200."""
    obra, exemplar = await obra_com_exemplar()

    resp = await client.post(
        f"/api/exemplares/{exemplar['id']}/baixar",
        json={"motivo": "danificado"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 200


# ─── BAI-E2E-002 ─────────────────────────────────────────────────────────────

async def test_bai_e2e_002_resposta_contem_estado_baixado(
    client: AsyncClient,
    auth_headers_admin: dict,
    obra_com_exemplar,
):
    """Resposta contém exemplar com estado='baixado'."""
    obra, exemplar = await obra_com_exemplar()

    resp = await client.post(
        f"/api/exemplares/{exemplar['id']}/baixar",
        json={"motivo": "danificado"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 200
    assert resp.json()["estado"] == "baixado"


# ─── BAI-E2E-003 ─────────────────────────────────────────────────────────────

async def test_bai_e2e_003_motivo_baixa_persistido_no_banco(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_com_exemplar,
):
    """motivo_baixa no banco reflete o motivo enviado."""
    obra, exemplar = await obra_com_exemplar()

    await client.post(
        f"/api/exemplares/{exemplar['id']}/baixar",
        json={"motivo": "danificado"},
        headers=auth_headers_admin,
    )

    result = await db_session.execute(
        text("SELECT motivo_baixa FROM exemplar WHERE id = :id"),
        {"id": uuid.UUID(exemplar["id"])},
    )
    assert result.scalar_one() == "danificado"


# ─── BAI-E2E-004, 005, 006 — motivos válidos ─────────────────────────────────

@pytest.mark.parametrize("motivo", ["danificado", "extraviado", "doado a outra biblioteca"])
async def test_bai_e2e_004_006_motivos_validos_sao_aceitos(
    motivo: str,
    client: AsyncClient,
    auth_headers_admin: dict,
    obra_com_exemplar,
):
    """Motivos 'danificado', 'extraviado' e 'doado a outra biblioteca' são aceitos."""
    obra, exemplar = await obra_com_exemplar()

    resp = await client.post(
        f"/api/exemplares/{exemplar['id']}/baixar",
        json={"motivo": motivo},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 200
    assert resp.json()["estado"] == "baixado"


# ─── BAI-E2E-007 ─────────────────────────────────────────────────────────────

async def test_bai_e2e_007_baixar_exemplar_emprestado_retorna_409(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_factory,
    leitor_factory,
    emprestimo_factory,
):
    """Tentar baixar exemplar com estado='emprestado' retorna 409."""
    obra = await obra_factory(db_session)
    leitor = await leitor_factory(db_session)
    ex = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    await emprestimo_factory(db_session, exemplar_id=ex.id, leitor_id=leitor.id, status="ativo")

    resp = await client.post(
        f"/api/exemplares/{ex.id}/baixar",
        json={"motivo": "extraviado"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 409


# ─── BAI-E2E-008 ─────────────────────────────────────────────────────────────

async def test_bai_e2e_008_mensagem_409_menciona_emprestado(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_factory,
    leitor_factory,
    emprestimo_factory,
):
    """Mensagem do 409 menciona 'emprestado'."""
    obra = await obra_factory(db_session)
    leitor = await leitor_factory(db_session)
    ex = await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    await emprestimo_factory(db_session, exemplar_id=ex.id, leitor_id=leitor.id, status="ativo")

    resp = await client.post(
        f"/api/exemplares/{ex.id}/baixar",
        json={"motivo": "extraviado"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 409
    assert "emprestado" in resp.json()["detail"].lower()


# ─── BAI-E2E-009 ─────────────────────────────────────────────────────────────

async def test_bai_e2e_009_baixar_exemplar_ja_baixado_retorna_409(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_baixado_factory,
):
    """Tentar baixar exemplar já com estado='baixado' retorna 409."""
    obra = await obra_factory(db_session)
    ex = await exemplar_baixado_factory(obra_id=obra.id, motivo_baixa="danificado")

    resp = await client.post(
        f"/api/exemplares/{ex.id}/baixar",
        json={"motivo": "danificado"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 409


# ─── BAI-E2E-010 ─────────────────────────────────────────────────────────────

async def test_bai_e2e_010_baixar_exemplar_inexistente_retorna_404(
    client: AsyncClient,
    auth_headers_admin: dict,
):
    """Tentar baixar exemplar inexistente retorna 404."""
    resp = await client.post(
        f"/api/exemplares/{uuid.uuid4()}/baixar",
        json={"motivo": "danificado"},
        headers=auth_headers_admin,
    )

    assert resp.status_code == 404


# ─── BAI-E2E-011 ─────────────────────────────────────────────────────────────

async def test_bai_e2e_011_baixa_gera_registro_inventario_log_com_acao_baixado(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_com_exemplar,
):
    """Registro em inventario_log com acao='baixado' após baixa bem-sucedida."""
    obra, exemplar = await obra_com_exemplar()

    await client.post(
        f"/api/exemplares/{exemplar['id']}/baixar",
        json={"motivo": "danificado"},
        headers=auth_headers_admin,
    )

    result = await db_session.execute(
        text(
            "SELECT COUNT(*) FROM inventario_log "
            "WHERE exemplar_id = :eid AND acao = 'baixado'"
        ),
        {"eid": uuid.UUID(exemplar["id"])},
    )
    assert result.scalar_one() >= 1


# ─── BAI-E2E-012 ─────────────────────────────────────────────────────────────

async def test_bai_e2e_012_operador_keycloak_id_correto_no_log(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_com_exemplar,
):
    """operador_keycloak_id no log reflete o token do usuário autenticado."""
    obra, exemplar = await obra_com_exemplar()

    await client.post(
        f"/api/exemplares/{exemplar['id']}/baixar",
        json={"motivo": "danificado"},
        headers=auth_headers_admin,
    )

    result = await db_session.execute(
        text(
            "SELECT operador_keycloak_id FROM inventario_log "
            "WHERE exemplar_id = :eid AND acao = 'baixado' "
            "ORDER BY timestamp DESC LIMIT 1"
        ),
        {"eid": uuid.UUID(exemplar["id"])},
    )
    # auth_headers_admin usa "Bearer test-token-admin" → get_current_user retorna "test-token-admin"
    assert result.scalar_one() == "test-token-admin"


# ─── BAI-E2E-013 ─────────────────────────────────────────────────────────────

async def test_bai_e2e_013_exemplar_baixado_nao_aparece_como_disponivel(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_com_exemplar,
):
    """Exemplar baixado não está com estado='disponivel' no banco."""
    obra, exemplar = await obra_com_exemplar()

    await client.post(
        f"/api/exemplares/{exemplar['id']}/baixar",
        json={"motivo": "danificado"},
        headers=auth_headers_admin,
    )

    result = await db_session.execute(
        text("SELECT estado FROM exemplar WHERE id = :id"),
        {"id": uuid.UUID(exemplar["id"])},
    )
    estado = result.scalar_one()
    assert estado == "baixado"
    assert estado != "disponivel"


# ─── BAI-E2E-014 ─────────────────────────────────────────────────────────────

async def test_bai_e2e_014_sem_token_retorna_401(client: AsyncClient):
    """Endpoint sem token retorna 401."""
    resp = await client.post(
        f"/api/exemplares/{uuid.uuid4()}/baixar",
        json={"motivo": "danificado"},
    )
    assert resp.status_code == 401


# ─── BAI-E2E-015 ─────────────────────────────────────────────────────────────

async def test_bai_e2e_015_token_operador_e_aceito_no_mvp(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """
    No MVP, qualquer token Bearer válido é aceito (role validation pós-MVP via Keycloak).
    O teste documenta o comportamento atual e o esperado após integração de roles.
    """
    resp = await client.post(
        f"/api/exemplares/{uuid.uuid4()}/baixar",
        json={"motivo": "danificado"},
        headers=auth_headers_operador,
    )
    # MVP: 404 (exemplar não existe mas token é aceito); pós-MVP: 403
    assert resp.status_code in (404, 403)
