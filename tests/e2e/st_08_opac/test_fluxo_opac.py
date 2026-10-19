"""
Teste E2E — Jornada completa do OPAC (US-028 + US-029 + US-030)
Caso: OPAC-E2E-029

Visitante anônimo busca uma obra esgotada, abre os detalhes, se pré-cadastra,
é ativado no balcão e, autenticado, entra na fila de reserva.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.st_08_opac.conftest import (
    exemplar_factory,
    gerar_cpf_valido,
    leitor_factory,
    obra_factory,
    token_leitor,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_opac_e2e_029_jornada_visitante_ate_reserva(
    client: AsyncClient, db_session: AsyncSession, auth_headers_operador: dict
) -> None:
    tag = f"jornada{uuid.uuid4().hex[:6]}"
    obra = await obra_factory(db_session, titulo=f"O Cortiço {tag}", autores=["Aluísio Azevedo"])
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    outro_leitor = await leitor_factory(db_session)
    checkout = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(outro_leitor.id)},
        headers=auth_headers_operador,
    )
    assert checkout.status_code == 201

    # 1. Visitante busca no catálogo e vê "Emprestado".
    catalogo = (await client.get("/api/obras/publico", params={"q": tag})).json()
    assert catalogo["items"][0]["disponivel"] is False

    # 2. Abre os detalhes: nenhum disponível, um emprestado, primeiro no ranking.
    detalhe = (await client.get(f"/api/obras/{obra.id}/publico")).json()
    assert (detalhe["exemplares_disponiveis"], detalhe["exemplares_emprestados"]) == (0, 1)
    assert detalhe["posicao_ranking"] == 1

    # 3. Tenta reservar sem login → 401 (o frontend redireciona ao Keycloak).
    anonimo = await client.post("/api/reservas/minhas", json={"obra_id": str(obra.id)})
    assert anonimo.status_code == 401

    # 4. Pré-cadastro; logado mas pendente, a reserva é recusada.
    cpf = gerar_cpf_valido(mascarado=True)
    email = f"{tag}@opac.example.com"
    cadastro = await client.post("/api/leitores", json={"nome": "Nova Leitora", "cpf": cpf, "email": email})
    assert cadastro.status_code == 201
    pendente = await client.post(
        "/api/reservas/minhas", json={"obra_id": str(obra.id)}, headers=token_leitor(email)
    )
    assert pendente.status_code == 400

    # 5. Operador encontra o leitor pendente no checkout e o ativa.
    busca = (await client.get("/api/leitores", params={"cpf": cpf}, headers=auth_headers_operador)).json()
    assert busca["status"] == "pendente"
    ativacao = await client.patch(f"/api/leitores/{busca['id']}/ativar", headers=auth_headers_operador)
    assert ativacao.status_code == 200

    # 6. Agora autenticada e ativa, a leitora entra na fila.
    reserva = await client.post(
        "/api/reservas/minhas", json={"obra_id": str(obra.id)}, headers=token_leitor(email)
    )
    assert reserva.status_code == 201
    assert reserva.json()["posicao_fila"] == 1
