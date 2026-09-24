"""
Testes E2E — Sub-Tarefa 2: Configurar Políticas de Circulação (US-035)
Casos: CFG-E2E-001 a CFG-E2E-007

Cobre:
  - GET /api/admin/configuracao retorna 200 com as 3 chaves e valores padrão
  - PUT /api/admin/configuracao/{chave} persiste novo valor (verificado via GET subsequente)
  - Endpoints protegidos por autenticação (401 sem token)
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# Chaves e valores padrão esperados conforme seed
_CHAVES_PADRAO = {
    "dias_emprestimo": "14",
    "max_renovacoes": "3",
    "max_emprestimos_por_leitor": "3",
}


# ─── CFG-E2E-001 ─────────────────────────────────────────────────────────────

async def test_cfg_e2e_001_get_configuracao_retorna_200(
    client: AsyncClient, auth_headers_admin: dict
) -> None:
    """CFG-E2E-001 — GET /api/admin/configuracao retorna 200 com lista de configurações."""
    response = await client.get("/api/admin/configuracao", headers=auth_headers_admin)
    assert response.status_code == 200


# ─── CFG-E2E-002 ─────────────────────────────────────────────────────────────

async def test_cfg_e2e_002_resposta_contem_tres_chaves(
    client: AsyncClient, auth_headers_admin: dict
) -> None:
    """CFG-E2E-002 — Resposta contém as 3 chaves de configuração esperadas."""
    response = await client.get("/api/admin/configuracao", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    chaves = {item["chave"] for item in data["items"]}
    for chave_esperada in _CHAVES_PADRAO:
        assert chave_esperada in chaves, f"Chave '{chave_esperada}' ausente na resposta"


# ─── CFG-E2E-003 ─────────────────────────────────────────────────────────────

async def test_cfg_e2e_003_valores_padrao_corretos(
    client: AsyncClient, auth_headers_admin: dict
) -> None:
    """CFG-E2E-003 — Valores padrão são '14', '3', '3' para as respectivas chaves."""
    response = await client.get("/api/admin/configuracao", headers=auth_headers_admin)
    assert response.status_code == 200
    items = {item["chave"]: item["valor"] for item in response.json()["items"]}
    for chave, valor_esperado in _CHAVES_PADRAO.items():
        assert items.get(chave) == valor_esperado, (
            f"Chave '{chave}': esperado '{valor_esperado}', obtido '{items.get(chave)}'"
        )


# ─── CFG-E2E-004 ─────────────────────────────────────────────────────────────

async def test_cfg_e2e_004_put_configuracao_retorna_200(
    client: AsyncClient, auth_headers_admin: dict
) -> None:
    """CFG-E2E-004 — PUT /api/admin/configuracao/dias_emprestimo retorna 200 com novo valor."""
    response = await client.put(
        "/api/admin/configuracao/dias_emprestimo",
        json={"valor": "21"},
        headers=auth_headers_admin,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["chave"] == "dias_emprestimo"
    assert data["valor"] == "21"


# ─── CFG-E2E-005 ─────────────────────────────────────────────────────────────

async def test_cfg_e2e_005_put_persiste_e_get_reflete_novo_valor(
    client: AsyncClient, auth_headers_admin: dict
) -> None:
    """CFG-E2E-005 — Após PUT, GET /api/admin/configuracao reflete o novo valor."""
    # Primeiro atualiza
    put_resp = await client.put(
        "/api/admin/configuracao/dias_emprestimo",
        json={"valor": "21"},
        headers=auth_headers_admin,
    )
    assert put_resp.status_code == 200

    # Depois confirma via GET
    get_resp = await client.get("/api/admin/configuracao", headers=auth_headers_admin)
    assert get_resp.status_code == 200
    items = {item["chave"]: item["valor"] for item in get_resp.json()["items"]}
    assert items.get("dias_emprestimo") == "21", (
        f"Esperado '21' após PUT, obtido '{items.get('dias_emprestimo')}'"
    )


# ─── CFG-E2E-006 ─────────────────────────────────────────────────────────────

async def test_cfg_e2e_006_get_sem_token_retorna_401(client: AsyncClient) -> None:
    """CFG-E2E-006 — GET /api/admin/configuracao sem token JWT retorna 401."""
    response = await client.get("/api/admin/configuracao")
    assert response.status_code == 401


# ─── CFG-E2E-007 ─────────────────────────────────────────────────────────────

async def test_cfg_e2e_007_put_sem_token_retorna_401(client: AsyncClient) -> None:
    """CFG-E2E-007 — PUT /api/admin/configuracao/{chave} sem token JWT retorna 401."""
    response = await client.put(
        "/api/admin/configuracao/dias_emprestimo",
        json={"valor": "30"},
    )
    assert response.status_code == 401
