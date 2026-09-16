"""
Testes e2e — US-010: Criar Exemplares Físicos (parte 1)
Sub-Tarefa 4 do plano ST-03.

Cobre os casos EXP-E2E-001 a EXP-E2E-009.

Estratégia:
  - A obra é criada via obra_factory (direto no banco) para isolar o setup
    do teste do endpoint de obras (que pode não estar implementado ainda).
  - As asserções verificam: quantidade, formato do codigo_qr, unicidade,
    vinculação à obra e proteção por autenticação.

Marcados com xfail até que o endpoint POST /api/obras/{obra_id}/exemplares seja implementado.
"""

from __future__ import annotations

import re
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.st_03_catalogacao.conftest import obra_factory

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# Padrão esperado para códigos QR: LIB-{ANO}-{SEQUENCIAL:05d}
CODIGO_QR_PATTERN = re.compile(r"^LIB-\d{4}-\d{5}$")

# UUID inexistente para testar 404
OBRA_ID_INEXISTENTE = "00000000-0000-0000-0000-000000000099"


# ─── EXP-E2E-001: POST com quantidade=3 retorna 201 e 3 exemplares ────────────

@pytest.mark.xfail(
    reason="Endpoint POST /api/obras/{obra_id}/exemplares não implementado", strict=False
)
async def test_exp_e2e_001_criar_3_exemplares_retorna_201(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    EXP-E2E-001 — POST /api/obras/{obra_id}/exemplares com quantidade=3 retorna 201 e 3 exemplares.
    US-010: "POST /api/obras/{obra_id}/exemplares cria N exemplares"
    """
    obra = await obra_factory(db_session, titulo="Obra para Exemplares")

    response = await client.post(
        f"/api/obras/{obra.id}/exemplares",
        json={"quantidade": 3, "localizacao_estante": "A-01"},
        headers=auth_headers_operador,
    )

    assert response.status_code == 201
    exemplares = response.json()
    assert isinstance(exemplares, list)
    assert len(exemplares) == 3


# ─── EXP-E2E-002: cada exemplar possui codigo_qr não nulo e não vazio ─────────

@pytest.mark.xfail(
    reason="Endpoint POST /api/obras/{obra_id}/exemplares não implementado", strict=False
)
async def test_exp_e2e_002_exemplares_possuem_codigo_qr(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    EXP-E2E-002 — Cada exemplar criado possui campo codigo_qr não nulo e não vazio.
    US-010: "cada um com codigo_qr único sequencial"
    """
    obra = await obra_factory(db_session, titulo="Obra QR Não Nulo")

    response = await client.post(
        f"/api/obras/{obra.id}/exemplares",
        json={"quantidade": 2, "localizacao_estante": "B-02"},
        headers=auth_headers_operador,
    )

    assert response.status_code == 201
    for exemplar in response.json():
        assert exemplar.get("codigo_qr") is not None
        assert exemplar["codigo_qr"] != ""


# ─── EXP-E2E-003: codigo_qr segue o formato LIB-{ANO}-{SEQUENCIAL:05d} ───────

@pytest.mark.xfail(
    reason="Endpoint POST /api/obras/{obra_id}/exemplares não implementado", strict=False
)
async def test_exp_e2e_003_formato_codigo_qr(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    EXP-E2E-003 — codigo_qr dos exemplares segue o formato LIB-{ANO}-{SEQUENCIAL:05d}.
    US-010: "formato LIB-{ANO}-{SEQUENCIAL:05d}"
    Ex: "LIB-2025-00001", "LIB-2025-00002"
    """
    obra = await obra_factory(db_session, titulo="Obra Formato QR")

    response = await client.post(
        f"/api/obras/{obra.id}/exemplares",
        json={"quantidade": 2, "localizacao_estante": "C-03"},
        headers=auth_headers_operador,
    )

    assert response.status_code == 201
    for exemplar in response.json():
        codigo_qr = exemplar["codigo_qr"]
        assert CODIGO_QR_PATTERN.match(codigo_qr), (
            f"codigo_qr '{codigo_qr}' não corresponde ao padrão LIB-YYYY-NNNNN"
        )


# ─── EXP-E2E-004: os 3 codigo_qr da mesma chamada são distintos ───────────────

@pytest.mark.xfail(
    reason="Endpoint POST /api/obras/{obra_id}/exemplares não implementado", strict=False
)
async def test_exp_e2e_004_codigos_qr_unicos_na_mesma_chamada(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    EXP-E2E-004 — Os 3 codigo_qr retornados na mesma chamada são distintos.
    US-010: "código único sequencial"
    """
    obra = await obra_factory(db_session, titulo="Obra Unicidade QR")

    response = await client.post(
        f"/api/obras/{obra.id}/exemplares",
        json={"quantidade": 3, "localizacao_estante": "D-04"},
        headers=auth_headers_operador,
    )

    assert response.status_code == 201
    codigos = [e["codigo_qr"] for e in response.json()]
    assert len(set(codigos)) == len(codigos), (
        f"Códigos QR duplicados na mesma chamada: {codigos}"
    )


# ─── EXP-E2E-005: segunda chamada produz codigos_qr distintos da primeira ─────

@pytest.mark.xfail(
    reason="Endpoint POST /api/obras/{obra_id}/exemplares não implementado", strict=False
)
async def test_exp_e2e_005_codigos_qr_unicos_entre_chamadas(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    EXP-E2E-005 — Segunda chamada de criação produz codigo_qr distintos dos da primeira chamada.
    US-010: unicidade global do sequencial.

    Ex: 1ª chamada → ["LIB-2025-00001", "LIB-2025-00002"]
        2ª chamada → ["LIB-2025-00003", "LIB-2025-00004"]
    """
    obra = await obra_factory(db_session, titulo="Obra Unicidade Global QR")

    resp1 = await client.post(
        f"/api/obras/{obra.id}/exemplares",
        json={"quantidade": 2, "localizacao_estante": "E-05"},
        headers=auth_headers_operador,
    )
    resp2 = await client.post(
        f"/api/obras/{obra.id}/exemplares",
        json={"quantidade": 2, "localizacao_estante": "E-05"},
        headers=auth_headers_operador,
    )

    assert resp1.status_code == 201
    assert resp2.status_code == 201

    codigos1 = {e["codigo_qr"] for e in resp1.json()}
    codigos2 = {e["codigo_qr"] for e in resp2.json()}

    # Nenhum código da segunda chamada deve coincidir com a primeira
    colisoes = codigos1 & codigos2
    assert not colisoes, f"Colisão de códigos QR entre chamadas: {colisoes}"


# ─── EXP-E2E-006: obra_id inexistente retorna 404 ─────────────────────────────

@pytest.mark.xfail(
    reason="Endpoint POST /api/obras/{obra_id}/exemplares não implementado", strict=False
)
async def test_exp_e2e_006_obra_inexistente_retorna_404(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """
    EXP-E2E-006 — POST /api/obras/{obra_id}/exemplares para obra_id inexistente retorna 404.
    US-010: obra deve existir (dep. US-009)
    """
    response = await client.post(
        f"/api/obras/{OBRA_ID_INEXISTENTE}/exemplares",
        json={"quantidade": 1, "localizacao_estante": "X-99"},
        headers=auth_headers_operador,
    )
    assert response.status_code == 404


# ─── EXP-E2E-007: sem token JWT retorna 401 ───────────────────────────────────

@pytest.mark.xfail(
    reason="Endpoint POST /api/obras/{obra_id}/exemplares não implementado", strict=False
)
async def test_exp_e2e_007_sem_token_retorna_401(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    EXP-E2E-007 — POST /api/obras/{obra_id}/exemplares sem token JWT retorna 401.
    US-010: "endpoint de criação exige autenticação"
    """
    obra = await obra_factory(db_session, titulo="Obra Auth 401")

    response = await client.post(
        f"/api/obras/{obra.id}/exemplares",
        json={"quantidade": 1, "localizacao_estante": "F-06"},
    )
    assert response.status_code == 401


# ─── EXP-E2E-008: role não autorizada retorna 403 ─────────────────────────────

@pytest.mark.xfail(
    reason="Endpoint POST /api/obras/{obra_id}/exemplares não implementado", strict=False
)
async def test_exp_e2e_008_role_nao_autorizada_retorna_403(
    client: AsyncClient,
    auth_headers_leitor: dict,
    db_session: AsyncSession,
):
    """
    EXP-E2E-008 — POST /api/obras/{obra_id}/exemplares com role não autorizada retorna 403.
    US-010: "role `admin` ou `operador`"
    """
    obra = await obra_factory(db_session, titulo="Obra Auth 403")

    response = await client.post(
        f"/api/obras/{obra.id}/exemplares",
        json={"quantidade": 1, "localizacao_estante": "G-07"},
        headers=auth_headers_leitor,
    )
    assert response.status_code == 403


# ─── EXP-E2E-009: exemplares criados estão vinculados ao obra_id correto ──────

@pytest.mark.xfail(
    reason="Endpoint POST /api/obras/{obra_id}/exemplares não implementado", strict=False
)
async def test_exp_e2e_009_exemplares_vinculados_ao_obra_id(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    EXP-E2E-009 — Exemplares criados estão vinculados ao obra_id correto no banco.
    US-010: FK para obra.
    """
    obra = await obra_factory(db_session, titulo="Obra Vinculação FK")

    response = await client.post(
        f"/api/obras/{obra.id}/exemplares",
        json={"quantidade": 2, "localizacao_estante": "H-08"},
        headers=auth_headers_operador,
    )

    assert response.status_code == 201
    for exemplar in response.json():
        assert str(exemplar["obra_id"]) == str(obra.id), (
            f"Exemplar vinculado ao obra_id errado: esperado {obra.id}, "
            f"recebido {exemplar['obra_id']}"
        )
