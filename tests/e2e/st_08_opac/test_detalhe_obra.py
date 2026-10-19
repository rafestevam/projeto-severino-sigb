"""
Testes E2E — US-029: Página de detalhes da obra e reserva pelo OPAC
Casos: OPAC-E2E-010 a OPAC-E2E-020

Cobre:
  - GET /api/obras/{id}/publico responde sem Authorization, com contagens corretas
  - Contagens acompanham checkout e devolução reais (POST /api/emprestimos)
  - posicao_ranking coerente com total_emprestimos (empates e obra nunca emprestada)
  - 404 para id inexistente e para obra fora do catálogo (só baixados)
  - POST /api/reservas/minhas: sem token → 401; token sem leitor vinculado ou com
    e-mail não verificado → 403;
    leitor pendente → 400; obra com exemplar disponível → 400; sucesso → 201 com
    posicao_fila; segunda reserva → 409; leitor_id do body é ignorado
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.reserva import ReservaModel
from tests.e2e.st_08_opac.conftest import (
    exemplar_factory,
    leitor_factory,
    obra_factory,
    token_leitor,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def _detalhe(client: AsyncClient, obra_id) -> dict:
    response = await client.get(f"/api/obras/{obra_id}/publico")
    assert response.status_code == 200, response.text
    return response.json()


async def _obra_com_total(db_session: AsyncSession, titulo: str, total: int):
    obra = await obra_factory(db_session, titulo=titulo)
    obra.total_emprestimos = total
    await db_session.flush()
    await exemplar_factory(db_session, obra_id=obra.id)
    return obra


# ─── OPAC-E2E-010 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_010_detalhe_publico_com_contagens(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-010 — detalhes completos e contagens, ignorando exemplares baixados."""
    obra = await obra_factory(
        db_session, titulo="Detalhe OPAC", autores=["Autora X"], editora="Ed", ano=2001
    )
    await exemplar_factory(db_session, obra_id=obra.id, estado="disponivel")
    await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    await exemplar_factory(db_session, obra_id=obra.id, estado="baixado")

    body = await _detalhe(client, obra.id)

    assert body["titulo"] == "Detalhe OPAC"
    assert body["autores"] == ["Autora X"]
    assert (body["editora"], body["ano"]) == ("Ed", 2001)
    assert body["sinopse"] is None
    assert body["exemplares_disponiveis"] == 1
    assert body["exemplares_emprestados"] == 2
    assert body["disponivel"] is True
    assert body["posicao_ranking"] is None
    for campo in ("isbn", "created_at", "cpf_hash", "leitor_id", "email", "telefone"):
        assert campo not in body


# ─── OPAC-E2E-011 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_011_contagens_acompanham_checkout_e_devolucao(
    client: AsyncClient, db_session: AsyncSession, auth_headers_operador: dict
) -> None:
    """OPAC-E2E-011 — checkout e devolução pelo balcão refletem no detalhe público."""
    obra = await obra_factory(db_session, titulo="Obra Circulante")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session)

    checkout = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor.id)},
        headers=auth_headers_operador,
    )
    assert checkout.status_code == 201, checkout.text
    depois_checkout = await _detalhe(client, obra.id)

    devolucao = await client.post(
        f"/api/emprestimos/{checkout.json()['id']}/devolver", headers=auth_headers_operador
    )
    assert devolucao.status_code == 200, devolucao.text
    depois_devolucao = await _detalhe(client, obra.id)

    assert (depois_checkout["exemplares_disponiveis"], depois_checkout["exemplares_emprestados"]) == (0, 1)
    assert depois_checkout["posicao_ranking"] == 1
    assert (depois_devolucao["exemplares_disponiveis"], depois_devolucao["exemplares_emprestados"]) == (1, 0)


# ─── OPAC-E2E-012 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_012_ranking_coerente_com_total_emprestimos(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-012 — "Preferidos da Galera": empates compartilham a posição."""
    primeira = await _obra_com_total(db_session, "Ranking A", 50)
    empatada_1 = await _obra_com_total(db_session, "Ranking B", 20)
    empatada_2 = await _obra_com_total(db_session, "Ranking C", 20)
    ultima = await _obra_com_total(db_session, "Ranking D", 1)

    posicoes = [
        (await _detalhe(client, o.id))["posicao_ranking"]
        for o in (primeira, empatada_1, empatada_2, ultima)
    ]

    assert posicoes == [1, 2, 2, 4]


# ─── OPAC-E2E-013 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_013_id_inexistente_retorna_404(client: AsyncClient) -> None:
    """OPAC-E2E-013 — UUID inexistente."""
    response = await client.get("/api/obras/00000000-0000-0000-0000-000000000000/publico")
    assert response.status_code == 404


# ─── OPAC-E2E-014 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_014_obra_fora_do_catalogo_retorna_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-014 — obra só com exemplares baixados não tem existência revelada."""
    obra = await obra_factory(db_session, titulo="Obra Baixada")
    await exemplar_factory(db_session, obra_id=obra.id, estado="baixado")

    response = await client.get(f"/api/obras/{obra.id}/publico")

    assert response.status_code == 404


# ─── Reserva online (POST /api/reservas/minhas) ──────────────────────────────

async def _obra_toda_emprestada(db_session: AsyncSession):
    obra = await obra_factory(db_session, titulo="Obra Esgotada")
    await exemplar_factory(db_session, obra_id=obra.id, estado="emprestado")
    return obra


async def test_opac_e2e_015_reserva_sem_token_retorna_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-015 — anônimo não reserva (o frontend redireciona ao Keycloak)."""
    obra = await _obra_toda_emprestada(db_session)
    response = await client.post("/api/reservas/minhas", json={"obra_id": str(obra.id)})
    assert response.status_code == 401


async def test_opac_e2e_016_token_sem_leitor_vinculado_retorna_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-016 — e-mail do token sem leitor correspondente."""
    obra = await _obra_toda_emprestada(db_session)
    response = await client.post(
        "/api/reservas/minhas",
        json={"obra_id": str(obra.id)},
        headers=token_leitor("ninguem@opac.example.com"),
    )
    assert response.status_code == 403


async def test_opac_e2e_016b_email_nao_verificado_retorna_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-016b — e-mail não verificado no Keycloak não identifica o leitor."""
    obra = await _obra_toda_emprestada(db_session)
    await leitor_factory(db_session, email="naoverificado@opac.example.com")

    response = await client.post(
        "/api/reservas/minhas",
        json={"obra_id": str(obra.id)},
        headers=token_leitor("naoverificado@opac.example.com", email_verified=False),
    )

    assert response.status_code == 403


async def test_opac_e2e_017_leitor_pendente_retorna_400(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-017 — leitor pré-cadastrado ainda não ativado não reserva."""
    obra = await _obra_toda_emprestada(db_session)
    await leitor_factory(db_session, email="pendente@opac.example.com", ativo=False)

    response = await client.post(
        "/api/reservas/minhas",
        json={"obra_id": str(obra.id)},
        headers=token_leitor("pendente@opac.example.com"),
    )

    assert response.status_code == 400


async def test_opac_e2e_018_obra_com_exemplar_disponivel_retorna_400(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-018 — reserva só faz sentido sem exemplar disponível."""
    obra = await obra_factory(db_session, titulo="Obra Livre")
    await exemplar_factory(db_session, obra_id=obra.id, estado="disponivel")
    await leitor_factory(db_session, email="ativo@opac.example.com")

    response = await client.post(
        "/api/reservas/minhas",
        json={"obra_id": str(obra.id)},
        headers=token_leitor("ativo@opac.example.com"),
    )

    assert response.status_code == 400


async def test_opac_e2e_019_reserva_com_sucesso_usa_leitor_do_token(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-019 — 201 com posicao_fila; o leitor_id enviado no body é ignorado."""
    obra = await _obra_toda_emprestada(db_session)
    leitor = await leitor_factory(db_session, email="Leitora@OPAC.example.com")
    outro = await leitor_factory(db_session)

    response = await client.post(
        "/api/reservas/minhas",
        json={"obra_id": str(obra.id), "leitor_id": str(outro.id)},
        headers=token_leitor("leitora@opac.example.com"),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["posicao_fila"] == 1
    assert body["leitor_id"] == str(leitor.id)
    reservas = (
        await db_session.execute(select(ReservaModel).where(ReservaModel.obra_id == obra.id))
    ).scalars().all()
    assert [r.leitor_id for r in reservas] == [leitor.id]


async def test_opac_e2e_020_segunda_reserva_retorna_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-020 — o leitor já está na fila desta obra."""
    obra = await _obra_toda_emprestada(db_session)
    await leitor_factory(db_session, email="fila@opac.example.com")
    headers = token_leitor("fila@opac.example.com")

    primeira = await client.post("/api/reservas/minhas", json={"obra_id": str(obra.id)}, headers=headers)
    segunda = await client.post("/api/reservas/minhas", json={"obra_id": str(obra.id)}, headers=headers)

    assert primeira.status_code == 201
    assert segunda.status_code == 409
