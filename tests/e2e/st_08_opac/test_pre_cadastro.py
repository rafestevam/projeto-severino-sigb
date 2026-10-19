"""
Testes E2E — US-030: Pré-cadastro de leitor pelo OPAC
Casos: OPAC-E2E-021 a OPAC-E2E-028

Cobre:
  - POST /api/leitores é público e cria leitor com ativo=false (status pendente)
  - Apenas o hash do CPF normalizado é persistido
  - CPF mascarado e não mascarado colidem → 409 sem dados no corpo
  - Colisão também com leitor cadastrado no balcão (checkout com CPF mascarado)
  - CPF inválido → 422
  - Leitor pendente não consegue checkout (LeitorInativoError → 400)
  - Operador ativa (PATCH /api/leitores/{id}/ativar) e o checkout passa a funcionar
  - GET /api/leitores?cpf= devolve status "pendente"/"ativo"
"""

from __future__ import annotations

import hashlib

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.leitor import LeitorModel
from tests.e2e.st_08_opac.conftest import (
    exemplar_factory,
    gerar_cpf_valido,
    leitor_factory,
    mascarar_cpf,
    obra_factory,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _hash(cpf_digitos: str) -> str:
    return hashlib.sha256(cpf_digitos.encode()).hexdigest()


async def _leitor_por_cpf(db_session: AsyncSession, cpf_digitos: str) -> LeitorModel | None:
    result = await db_session.execute(
        select(LeitorModel).where(LeitorModel.cpf_hash == _hash(cpf_digitos))
    )
    return result.scalar_one_or_none()


# ─── OPAC-E2E-021 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_021_pre_cadastro_publico_cria_leitor_pendente(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-021 — 201 sem Authorization; leitor nasce com ativo=false."""
    cpf = gerar_cpf_valido()

    response = await client.post(
        "/api/leitores",
        json={"nome": "Visitante OPAC", "cpf": mascarar_cpf(cpf), "email": "Visitante@OPAC.example.com"},
    )

    assert response.status_code == 201
    assert response.json() == {"status": "pendente"}
    leitor = await _leitor_por_cpf(db_session, cpf)
    assert leitor is not None
    assert leitor.ativo is False
    assert leitor.telefone is None
    assert leitor.email == "visitante@opac.example.com"
    assert cpf not in leitor.cpf_hash


# ─── OPAC-E2E-022 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_022_pre_cadastro_sem_contatos_opcionais(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-022 — telefone e e-mail são opcionais."""
    cpf = gerar_cpf_valido()

    response = await client.post("/api/leitores", json={"nome": "Sem Contato", "cpf": cpf})

    assert response.status_code == 201
    leitor = await _leitor_por_cpf(db_session, cpf)
    assert leitor is not None and leitor.email is None and leitor.telefone is None


# ─── OPAC-E2E-023 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_023_cpf_mascarado_e_nao_mascarado_colidem_com_409(
    client: AsyncClient,
) -> None:
    """OPAC-E2E-023 — duplicidade detectada independentemente da máscara, sem vazar dados."""
    cpf = gerar_cpf_valido()
    primeiro = await client.post("/api/leitores", json={"nome": "Primeira Pessoa", "cpf": cpf})

    segundo = await client.post(
        "/api/leitores", json={"nome": "Segunda Pessoa", "cpf": mascarar_cpf(cpf)}
    )

    assert primeiro.status_code == 201
    assert segundo.status_code == 409
    assert segundo.json() == {
        "detail": "Já existe um cadastro para este CPF. Procure o balcão da biblioteca."
    }


# ─── OPAC-E2E-024 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_024_colide_com_leitor_cadastrado_no_balcao(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-024 — leitor já existente (balcão) também gera 409."""
    cpf = gerar_cpf_valido()
    await leitor_factory(db_session, cpf=cpf)

    response = await client.post("/api/leitores", json={"nome": "Repetido", "cpf": mascarar_cpf(cpf)})

    assert response.status_code == 409


# ─── OPAC-E2E-025 ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cpf", ["111.111.111-11", "123.456.789-00", "123"])
async def test_opac_e2e_025_cpf_invalido_retorna_422(client: AsyncClient, cpf: str) -> None:
    """OPAC-E2E-025 — dígitos verificadores e formato validados na API."""
    response = await client.post("/api/leitores", json={"nome": "CPF Inválido", "cpf": cpf})
    assert response.status_code == 422


# ─── OPAC-E2E-026 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_026_leitor_pendente_nao_faz_checkout(
    client: AsyncClient, db_session: AsyncSession, auth_headers_operador: dict
) -> None:
    """OPAC-E2E-026 — pendente = inativo: o balcão recusa o empréstimo."""
    cpf = gerar_cpf_valido()
    await client.post("/api/leitores", json={"nome": "Pendente", "cpf": cpf})
    leitor = await _leitor_por_cpf(db_session, cpf)
    obra = await obra_factory(db_session, titulo="Obra Checkout Pendente")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)

    response = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor.id)},
        headers=auth_headers_operador,
    )

    assert response.status_code == 400


# ─── OPAC-E2E-027 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_027_ativacao_pelo_operador_libera_checkout(
    client: AsyncClient, db_session: AsyncSession, auth_headers_operador: dict
) -> None:
    """OPAC-E2E-027 — busca por CPF mostra pendente → ativar → checkout 201."""
    cpf = gerar_cpf_valido()
    await client.post("/api/leitores", json={"nome": "Futura Leitora", "cpf": cpf})

    busca = await client.get(
        "/api/leitores", params={"cpf": mascarar_cpf(cpf)}, headers=auth_headers_operador
    )
    assert busca.status_code == 200
    assert busca.json()["status"] == "pendente"
    leitor_id = busca.json()["id"]

    ativacao = await client.patch(f"/api/leitores/{leitor_id}/ativar", headers=auth_headers_operador)
    assert ativacao.status_code == 200
    assert ativacao.json()["status"] == "ativo"

    obra = await obra_factory(db_session, titulo="Obra Pós-Ativação")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    checkout = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": leitor_id},
        headers=auth_headers_operador,
    )
    assert checkout.status_code == 201, checkout.text


# ─── OPAC-E2E-028 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_028_ativacao_exige_token_e_leitor_existente(
    client: AsyncClient, auth_headers_operador: dict
) -> None:
    """OPAC-E2E-028 — ativação é rota de balcão: 401 sem token, 404 para id inexistente."""
    inexistente = "00000000-0000-0000-0000-000000000000"

    sem_token = await client.patch(f"/api/leitores/{inexistente}/ativar")
    nao_encontrado = await client.patch(
        f"/api/leitores/{inexistente}/ativar", headers=auth_headers_operador
    )

    assert sem_token.status_code == 401
    assert nao_encontrado.status_code == 404
