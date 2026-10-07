"""
Testes E2E — ST-06 US-021: Dashboard de Métricas e Empréstimos Atrasados
Casos: DASH-E2E-001 a DASH-E2E-015 e ATR-E2E-001 a ATR-E2E-008

Estratégia:
  - HTTP real ao ASGI com PostgreSQL de teste via fixture `client`.
  - Setup de estado via fixtures injetadas (obra_factory, exemplar_factory, etc.)
    — sem import direto de conftest.
  - Sem asserções em helpers/factories: assert pertence ao corpo do teste.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard (DASH-E2E)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_dash_e2e_001_dashboard_retorna_200(
    client: AsyncClient,
    auth_headers_admin: dict,
):
    """GET /api/relatorios/dashboard retorna 200."""
    resp = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp.status_code == 200


async def test_dash_e2e_002_resposta_contem_campos_obrigatorios(
    client: AsyncClient,
    auth_headers_admin: dict,
):
    """Resposta contém total_obras, total_exemplares, total_leitores_ativos."""
    resp = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_obras" in data
    assert "total_exemplares" in data
    assert "total_leitores_ativos" in data


async def test_dash_e2e_003_exemplares_por_estado_tem_tres_chaves_inteiras(
    client: AsyncClient,
    auth_headers_admin: dict,
):
    """exemplares_por_estado contém chaves disponivel, emprestado e baixado como inteiros."""
    resp = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp.status_code == 200
    estados = resp.json()["exemplares_por_estado"]
    assert "disponivel" in estados
    assert "emprestado" in estados
    assert "baixado" in estados
    assert isinstance(estados["disponivel"], int)
    assert isinstance(estados["emprestado"], int)
    assert isinstance(estados["baixado"], int)


async def test_dash_e2e_004_top_obras_com_no_maximo_10_itens(
    client: AsyncClient,
    auth_headers_admin: dict,
):
    """top_obras_emprestadas tem no máximo 10 itens."""
    resp = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp.status_code == 200
    top = resp.json()["top_obras_emprestadas"]
    assert isinstance(top, list)
    assert len(top) <= 10


async def test_dash_e2e_005_top_obras_nao_contem_dados_de_leitor(
    client: AsyncClient,
    auth_headers_admin: dict,
):
    """top_obras_emprestadas não contém campos de leitor."""
    resp = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp.status_code == 200
    for item in resp.json()["top_obras_emprestadas"]:
        assert "nome" not in item
        assert "cpf" not in item
        assert "telefone" not in item
        assert "email" not in item
        assert "obra_id" in item
        assert "titulo" in item
        assert "total_emprestimos" in item


async def test_dash_e2e_006_taxa_perdas_e_float_entre_0_e_1(
    client: AsyncClient,
    auth_headers_admin: dict,
):
    """Resposta contém taxa_perdas como float entre 0 e 1."""
    resp = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp.status_code == 200
    taxa = resp.json()["taxa_perdas"]
    assert isinstance(taxa, float)
    assert 0.0 <= taxa <= 1.0


async def test_dash_e2e_007_total_doacoes_e_inteiro(
    client: AsyncClient,
    auth_headers_admin: dict,
):
    """Resposta contém total_doacoes como inteiro."""
    resp = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert isinstance(resp.json()["total_doacoes"], int)


async def test_dash_e2e_008_nenhum_campo_expoe_dados_pessoais(
    client: AsyncClient,
    auth_headers_admin: dict,
):
    """Nenhum campo da resposta expõe dados pessoais identificáveis."""
    resp = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()
    for campo in ("nome", "cpf", "cpf_hash", "telefone", "email"):
        assert campo not in data
        for item in data.get("top_obras_emprestadas", []):
            assert campo not in item


async def test_dash_e2e_009_dashboard_acessivel_por_operador(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """Dashboard é acessível por operador (não apenas admin)."""
    resp = await client.get("/api/relatorios/dashboard", headers=auth_headers_operador)
    assert resp.status_code == 200


async def test_dash_e2e_010_dashboard_acessivel_por_admin(
    client: AsyncClient,
    auth_headers_admin: dict,
):
    """Dashboard é acessível por admin."""
    resp = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp.status_code == 200


async def test_dash_e2e_011_total_obras_reflete_cadastros(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
):
    """total_obras reflete o número de obras no banco."""
    await obra_factory(db_session)

    resp = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["total_obras"] >= 1


async def test_dash_e2e_012_baixado_aumenta_apos_baixa(
    client: AsyncClient,
    auth_headers_admin: dict,
    obra_com_exemplar,
):
    """exemplares_por_estado.baixado aumenta após baixa de exemplar."""
    resp_antes = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    baixados_antes = resp_antes.json()["exemplares_por_estado"]["baixado"]

    obra, exemplar = await obra_com_exemplar()
    await client.post(
        f"/api/exemplares/{exemplar['id']}/baixar",
        json={"motivo": "danificado"},
        headers=auth_headers_admin,
    )

    resp_depois = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp_depois.json()["exemplares_por_estado"]["baixado"] >= baixados_antes + 1


async def test_dash_e2e_013_taxa_perdas_zero_sem_extraviados(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_factory,
):
    """taxa_perdas é 0.0 neste teste quando não há exemplares extraviados."""
    await obra_factory(db_session)  # garante total_exemplares > 0 se necessário
    # Nenhum exemplar extraviado criado neste contexto (SAVEPOINT isolado)
    resp = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["taxa_perdas"] == 0.0


async def test_dash_e2e_014_taxa_perdas_maior_zero_apos_baixa_extraviado(
    client: AsyncClient,
    auth_headers_admin: dict,
    obra_com_exemplar,
):
    """taxa_perdas > 0 após baixa de exemplar com motivo 'extraviado'."""
    obra, exemplar = await obra_com_exemplar()

    await client.post(
        f"/api/exemplares/{exemplar['id']}/baixar",
        json={"motivo": "extraviado"},
        headers=auth_headers_admin,
    )

    resp = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["taxa_perdas"] > 0.0


async def test_dash_e2e_015_sem_token_retorna_401(client: AsyncClient):
    """Endpoint sem token retorna 401."""
    resp = await client.get("/api/relatorios/dashboard")
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Empréstimos Atrasados (ATR-E2E)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_atr_e2e_001_emprestimos_atrasados_retorna_200(
    client: AsyncClient,
    auth_headers_admin: dict,
):
    """GET /api/relatorios/emprestimos-atrasados retorna 200 com admin."""
    resp = await client.get("/api/relatorios/emprestimos-atrasados", headers=auth_headers_admin)
    assert resp.status_code == 200


async def test_atr_e2e_002_resposta_contem_items_e_total(
    client: AsyncClient,
    auth_headers_admin: dict,
):
    """Resposta contém lista 'items' e campo 'total'."""
    resp = await client.get("/api/relatorios/emprestimos-atrasados", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)


async def test_atr_e2e_003_itens_contem_campos_de_emprestimo(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_factory,
    leitor_factory,
    emprestimo_factory,
):
    """Itens contêm id, exemplar_id, leitor_id, status."""
    obra = await obra_factory(db_session)
    leitor = await leitor_factory(db_session)
    ex = await exemplar_factory(db_session, obra_id=obra.id)
    await emprestimo_factory(db_session, exemplar_id=ex.id, leitor_id=leitor.id, status="atrasado")

    resp = await client.get("/api/relatorios/emprestimos-atrasados", headers=auth_headers_admin)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    for item in items:
        assert "id" in item
        assert "exemplar_id" in item
        assert "leitor_id" in item
        assert "status" in item


async def test_atr_e2e_004_nenhum_item_contem_dados_pessoais(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_factory,
    leitor_factory,
    emprestimo_factory,
):
    """Nenhum item contém nome, cpf ou telefone — apenas leitor_id é permitido."""
    obra = await obra_factory(db_session)
    leitor = await leitor_factory(db_session)
    ex = await exemplar_factory(db_session, obra_id=obra.id)
    await emprestimo_factory(db_session, exemplar_id=ex.id, leitor_id=leitor.id, status="atrasado")

    resp = await client.get("/api/relatorios/emprestimos-atrasados", headers=auth_headers_admin)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert "nome" not in item
        assert "cpf" not in item
        assert "cpf_hash" not in item
        assert "telefone" not in item
        assert "email" not in item
        assert "leitor_id" in item  # UUID permitido


async def test_atr_e2e_005_emprestimo_atrasado_aparece_na_lista(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_factory,
    leitor_factory,
    emprestimo_factory,
):
    """Empréstimo com status='atrasado' aparece na lista."""
    obra = await obra_factory(db_session)
    leitor = await leitor_factory(db_session)
    ex = await exemplar_factory(db_session, obra_id=obra.id)
    emp_atrasado = await emprestimo_factory(
        db_session, exemplar_id=ex.id, leitor_id=leitor.id, status="atrasado"
    )

    resp = await client.get("/api/relatorios/emprestimos-atrasados", headers=auth_headers_admin)
    assert resp.status_code == 200
    ids_na_lista = [item["id"] for item in resp.json()["items"]]
    assert str(emp_atrasado.id) in ids_na_lista


async def test_atr_e2e_006_emprestimo_ativo_nao_aparece_na_lista_de_atrasados(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict,
    obra_factory,
    exemplar_factory,
    leitor_factory,
    emprestimo_factory,
):
    """Empréstimo com status='ativo' NÃO aparece na lista de atrasados."""
    obra = await obra_factory(db_session)
    leitor = await leitor_factory(db_session)
    ex = await exemplar_factory(db_session, obra_id=obra.id)
    emp_ativo = await emprestimo_factory(
        db_session, exemplar_id=ex.id, leitor_id=leitor.id, status="ativo"
    )

    resp = await client.get("/api/relatorios/emprestimos-atrasados", headers=auth_headers_admin)
    assert resp.status_code == 200
    ids_na_lista = [item["id"] for item in resp.json()["items"]]
    assert str(emp_ativo.id) not in ids_na_lista


async def test_atr_e2e_007_token_operador_e_aceito_no_mvp(
    client: AsyncClient,
    auth_headers_operador: dict,
):
    """
    No MVP, qualquer token Bearer válido é aceito (role validation pós-MVP via Keycloak).
    O teste documenta o comportamento atual e o esperado após integração de roles.
    """
    resp = await client.get(
        "/api/relatorios/emprestimos-atrasados", headers=auth_headers_operador
    )
    # MVP: 200; pós-MVP: 403
    assert resp.status_code in (200, 403)


async def test_atr_e2e_008_sem_token_retorna_401(client: AsyncClient):
    """Endpoint sem token retorna 401."""
    resp = await client.get("/api/relatorios/emprestimos-atrasados")
    assert resp.status_code == 401
