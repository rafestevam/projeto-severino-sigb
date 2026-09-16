"""
Testes e2e — US-010: Geração de Etiquetas PDF (parte 2)
Sub-Tarefa 5 do plano ST-03.

Cobre os casos ETQ-E2E-001 a ETQ-E2E-008.

Estratégia:
  - Exemplares são pré-criados via exemplar_factory (direto no banco) para isolar
    o setup do teste dos endpoints de obras/exemplares (que podem não estar implementados).
  - EtiquetaPdfService é usado na sua implementação real (sem mocks) — o e2e
    valida que o endpoint orquestra corretamente o serviço e entrega um PDF válido.
  - Apenas o banco é fakeado (SAVEPOINT revertido); nenhum I/O externo é feito.

Nota: os testes NÃO validam o conteúdo visual do PDF (QR Code, layout Pimaco).
Essa validação é responsabilidade dos testes unitários do EtiquetaPdfService.

Marcados com xfail até que o endpoint GET /api/exemplares/{codigo_qr}/etiqueta.pdf
seja implementado.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.st_03_catalogacao.conftest import exemplar_factory, obra_factory

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# Código QR que certamente não existirá no banco de teste
CODIGO_QR_INEXISTENTE = "LIB-0000-99999"


# ─── ETQ-E2E-001: GET retorna 200 ─────────────────────────────────────────────

@pytest.mark.xfail(
    reason="Endpoint GET /api/exemplares/{codigo_qr}/etiqueta.pdf não implementado",
    strict=False,
)
async def test_etq_e2e_001_retorna_200(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    ETQ-E2E-001 — GET /api/exemplares/{codigo_qr}/etiqueta.pdf retorna 200.
    US-010: "GET /api/exemplares/{codigo_qr}/etiqueta.pdf retorna PDF para impressão"
    """
    obra = await obra_factory(db_session, titulo="Obra Etiqueta 001")
    exemplar = await exemplar_factory(
        db_session, obra_id=obra.id, codigo_qr="LIB-2025-00001"
    )

    response = await client.get(
        f"/api/exemplares/{exemplar.codigo_qr}/etiqueta.pdf",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200


# ─── ETQ-E2E-002: Content-Type é application/pdf ──────────────────────────────

@pytest.mark.xfail(
    reason="Endpoint GET /api/exemplares/{codigo_qr}/etiqueta.pdf não implementado",
    strict=False,
)
async def test_etq_e2e_002_content_type_pdf(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    ETQ-E2E-002 — Content-Type da resposta é application/pdf.
    US-010: resposta deve ser um PDF.
    """
    obra = await obra_factory(db_session, titulo="Obra Etiqueta 002")
    exemplar = await exemplar_factory(
        db_session, obra_id=obra.id, codigo_qr="LIB-2025-00002"
    )

    response = await client.get(
        f"/api/exemplares/{exemplar.codigo_qr}/etiqueta.pdf",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")


# ─── ETQ-E2E-003: corpo começa com bytes %PDF ─────────────────────────────────

@pytest.mark.xfail(
    reason="Endpoint GET /api/exemplares/{codigo_qr}/etiqueta.pdf não implementado",
    strict=False,
)
async def test_etq_e2e_003_corpo_comeca_com_bytes_pdf(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    ETQ-E2E-003 — Corpo da resposta começa com os bytes %PDF (header de PDF válido).
    US-010: PDF gerado é estruturalmente válido.
    """
    obra = await obra_factory(db_session, titulo="Obra Etiqueta 003")
    exemplar = await exemplar_factory(
        db_session, obra_id=obra.id, codigo_qr="LIB-2025-00003"
    )

    response = await client.get(
        f"/api/exemplares/{exemplar.codigo_qr}/etiqueta.pdf",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    assert response.content[:4] == b"%PDF", (
        f"Resposta não começa com %PDF: {response.content[:16]!r}"
    )


# ─── ETQ-E2E-004: corpo não está vazio ────────────────────────────────────────

@pytest.mark.xfail(
    reason="Endpoint GET /api/exemplares/{codigo_qr}/etiqueta.pdf não implementado",
    strict=False,
)
async def test_etq_e2e_004_corpo_nao_esta_vazio(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    ETQ-E2E-004 — Corpo da resposta não está vazio (tamanho > 100 bytes).
    US-010: PDF gerado tem conteúdo.
    """
    obra = await obra_factory(db_session, titulo="Obra Etiqueta 004")
    exemplar = await exemplar_factory(
        db_session, obra_id=obra.id, codigo_qr="LIB-2025-00004"
    )

    response = await client.get(
        f"/api/exemplares/{exemplar.codigo_qr}/etiqueta.pdf",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200
    assert len(response.content) > 100, (
        f"PDF gerado muito pequeno: {len(response.content)} bytes"
    )


# ─── ETQ-E2E-005: codigo_qr inexistente retorna 404 ──────────────────────────

@pytest.mark.xfail(
    reason="Endpoint GET /api/exemplares/{codigo_qr}/etiqueta.pdf não implementado",
    strict=False,
)
async def test_etq_e2e_005_codigo_qr_inexistente_retorna_404(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """
    ETQ-E2E-005 — GET /api/exemplares/CODIGO_INEXISTENTE/etiqueta.pdf retorna 404.
    US-010: codigo_qr deve existir.
    """
    response = await client.get(
        f"/api/exemplares/{CODIGO_QR_INEXISTENTE}/etiqueta.pdf",
        headers=auth_headers_operador,
    )
    assert response.status_code == 404


# ─── ETQ-E2E-006: sem token JWT retorna 401 ───────────────────────────────────

@pytest.mark.xfail(
    reason="Endpoint GET /api/exemplares/{codigo_qr}/etiqueta.pdf não implementado",
    strict=False,
)
async def test_etq_e2e_006_sem_token_retorna_401(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    ETQ-E2E-006 — GET /api/exemplares/{codigo_qr}/etiqueta.pdf sem token JWT retorna 401.
    US-010: proteção de endpoint.
    """
    obra = await obra_factory(db_session, titulo="Obra Etiqueta 006")
    exemplar = await exemplar_factory(
        db_session, obra_id=obra.id, codigo_qr="LIB-2025-00006"
    )

    response = await client.get(
        f"/api/exemplares/{exemplar.codigo_qr}/etiqueta.pdf"
    )
    assert response.status_code == 401


# ─── ETQ-E2E-007: token de operador retorna 200 ───────────────────────────────

@pytest.mark.xfail(
    reason="Endpoint GET /api/exemplares/{codigo_qr}/etiqueta.pdf não implementado",
    strict=False,
)
async def test_etq_e2e_007_token_operador_retorna_200(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    ETQ-E2E-007 — GET /api/exemplares/{codigo_qr}/etiqueta.pdf com token de operador retorna 200.
    US-010: acesso de operador funciona.
    """
    obra = await obra_factory(db_session, titulo="Obra Etiqueta 007")
    exemplar = await exemplar_factory(
        db_session, obra_id=obra.id, codigo_qr="LIB-2025-00007"
    )

    response = await client.get(
        f"/api/exemplares/{exemplar.codigo_qr}/etiqueta.pdf",
        headers=auth_headers_operador,
    )
    assert response.status_code == 200


# ─── ETQ-E2E-008: múltiplos exemplares geram etiquetas individualmente ────────

@pytest.mark.xfail(
    reason="Endpoint GET /api/exemplares/{codigo_qr}/etiqueta.pdf não implementado",
    strict=False,
)
async def test_etq_e2e_008_multiplos_exemplares_sem_conflito(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
):
    """
    ETQ-E2E-008 — Múltiplos exemplares podem ter etiquetas geradas individualmente sem conflito.
    US-010: geração por exemplar.
    """
    obra = await obra_factory(db_session, titulo="Obra Etiqueta 008 Multi")
    exemplar_a = await exemplar_factory(
        db_session, obra_id=obra.id, codigo_qr="LIB-2025-00008"
    )
    exemplar_b = await exemplar_factory(
        db_session, obra_id=obra.id, codigo_qr="LIB-2025-00009"
    )

    for exemplar in [exemplar_a, exemplar_b]:
        response = await client.get(
            f"/api/exemplares/{exemplar.codigo_qr}/etiqueta.pdf",
            headers=auth_headers_operador,
        )
        assert response.status_code == 200, (
            f"Falha ao gerar etiqueta para {exemplar.codigo_qr}: {response.status_code}"
        )
        assert response.content[:4] == b"%PDF"
