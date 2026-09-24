"""
Testes E2E — Sub-Tarefa 8: Fluxo Completo de Circulação (Happy Path)
Casos: FLOW-C-001 a FLOW-C-003

Cobre:
  - FLOW-C-001: Jornada completa do operador (checkout → renovação → check-in QR → reserva ativada → listar)
  - FLOW-C-002: Política customizada dias_emprestimo=7 aplicada ao check-out
  - FLOW-C-003: Fluxo de atraso (checkout → job marca atrasado → check-in resolve)

Estratégia: leitores, obras e exemplares criados via factory (db_session) para
independência de routers não implementados (/api/leitores, /api/reservas).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.reserva import ReservaModel
from app.adapters.repositories.sqlalchemy_emprestimo_repository import (
    SQLAlchemyEmprestimoRepository,
)
from app.infrastructure.notificacao_gateway_stub import NotificacaoGatewayStub
from app.use_cases.marcar_atrasados import MarcarAtrasadosUseCase
from tests.e2e.st_04_circulacao.conftest import (
    emprestimo_factory,
    exemplar_factory,
    leitor_factory,
    obra_factory,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ─── FLOW-C-001 ──────────────────────────────────────────────────────────────

async def test_flow_c_001_jornada_completa_do_operador(
    client: AsyncClient,
    auth_headers_operador: dict,
    auth_headers_admin: dict,
    db_session: AsyncSession,
) -> None:
    """
    FLOW-C-001 — Jornada completa:
      Passo 1: Setup via factory (obra, exemplar, leitor A, leitor B)
      Passo 2: Leitor B faz reserva (inserida diretamente no banco)
      Passo 3: Check-out para leitor A via API
      Passo 4: Renovação via API
      Passo 5: Check-in por QR via API
      Passo 6: Reserva de leitor B ativada (verificada via db_session)
      Passo 7: Listar empréstimos com filtro confirma titulo_obra
    """
    # --- Passo 1 — Setup via factory ---
    obra = await obra_factory(db_session, titulo="Dom Casmurro FLOW-001")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id, codigo_qr="QR-FLOW-C-001")
    leitor_a = await leitor_factory(db_session, nome="Leitor A FLOW-001")
    leitor_b = await leitor_factory(db_session, nome="Leitor B FLOW-001")

    # --- Passo 2 — Reserva do leitor B (aguardando) ---
    reserva = ReservaModel(
        id=uuid.uuid4(),
        obra_id=obra.id,
        leitor_id=leitor_b.id,
        status="aguardando",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(reserva)
    await db_session.flush()
    await db_session.refresh(reserva)

    # --- Passo 3 — Check-out para leitor A ---
    before_checkout = datetime.now(tz=timezone.utc)
    checkout_resp = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor_a.id)},
        headers=auth_headers_operador,
    )
    after_checkout = datetime.now(tz=timezone.utc)
    assert checkout_resp.status_code == 201, f"Checkout falhou: {checkout_resp.text}"
    emprestimo_id = checkout_resp.json()["id"]
    assert checkout_resp.json()["status"] == "ativo"

    # Verifica data_prevista ~= now + 14d
    data_prevista = datetime.fromisoformat(checkout_resp.json()["data_prevista"])
    if data_prevista.tzinfo is None:
        data_prevista = data_prevista.replace(tzinfo=timezone.utc)
    lower_14d = before_checkout + timedelta(days=14) - timedelta(minutes=1)
    upper_14d = after_checkout + timedelta(days=14) + timedelta(minutes=1)
    assert lower_14d <= data_prevista <= upper_14d, (
        f"data_prevista {data_prevista} fora do intervalo do checkout [{lower_14d}, {upper_14d}]"
    )

    # Verifica exemplar.estado = "emprestado"
    resp_ex = await client.get(f"/api/exemplares/{exemplar.id}", headers=auth_headers_operador)
    assert resp_ex.json()["estado"] == "emprestado"

    # --- Passo 4 — Renovação ---
    before_ren = datetime.now(tz=timezone.utc)
    ren_resp = await client.post(
        f"/api/emprestimos/{emprestimo_id}/renovar",
        headers=auth_headers_operador,
    )
    after_ren = datetime.now(tz=timezone.utc)
    assert ren_resp.status_code == 200, f"Renovação falhou: {ren_resp.text}"
    assert ren_resp.json()["renovacoes"] == 1

    nova_prevista = datetime.fromisoformat(ren_resp.json()["data_prevista"])
    if nova_prevista.tzinfo is None:
        nova_prevista = nova_prevista.replace(tzinfo=timezone.utc)
    assert nova_prevista >= before_ren + timedelta(days=14) - timedelta(minutes=1)
    assert nova_prevista <= after_ren + timedelta(days=14) + timedelta(minutes=1)

    # --- Passo 5 — Check-in por QR ---
    checkin_resp = await client.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )
    assert checkin_resp.status_code == 200, f"Check-in falhou: {checkin_resp.text}"
    assert checkin_resp.json()["status"] == "devolvido"
    assert checkin_resp.json()["data_devolucao"] is not None

    # Verifica exemplar.estado = "disponivel"
    resp_ex2 = await client.get(f"/api/exemplares/{exemplar.id}", headers=auth_headers_operador)
    assert resp_ex2.json()["estado"] == "disponivel"

    # --- Passo 6 — Reserva de leitor B ativada ---
    await db_session.refresh(reserva)
    assert reserva.status == "disponivel", (
        f"Reserva deveria ser 'disponivel', obtido '{reserva.status}'"
    )

    # --- Passo 7 — Listar empréstimos confirma titulo_obra ---
    lst_resp = await client.get(
        f"/api/emprestimos?leitor_id={leitor_a.id}&status=devolvido",
        headers=auth_headers_operador,
    )
    assert lst_resp.status_code == 200
    items = lst_resp.json()["items"]
    assert len(items) >= 1
    item_devolvido = next(
        (i for i in items if i["id"] == emprestimo_id), None
    )
    assert item_devolvido is not None, "Empréstimo devolvido não aparece na listagem"
    assert item_devolvido["titulo_obra"] == "Dom Casmurro FLOW-001"


# ─── FLOW-C-002 ──────────────────────────────────────────────────────────────

async def test_flow_c_002_politica_customizada_refletida_no_checkout(
    client: AsyncClient,
    auth_headers_operador: dict,
    auth_headers_admin: dict,
    db_session: AsyncSession,
) -> None:
    """
    FLOW-C-002 — Política customizada:
      Passo 1: PUT dias_emprestimo = 7
      Passo 2: Checkout → data_prevista deve ser ~now + 7d (não 14d)
    """
    # --- Passo 1 — Atualizar política ---
    put_resp = await client.put(
        "/api/admin/configuracao/dias_emprestimo",
        json={"valor": "7"},
        headers=auth_headers_admin,
    )
    assert put_resp.status_code == 200, f"PUT configuracao falhou: {put_resp.text}"

    # --- Passo 2 — Criar obra, exemplar, leitor via factory e realizar checkout ---
    obra = await obra_factory(db_session, titulo="Obra Politica 7d FLOW-002")
    exemplar = await exemplar_factory(db_session, obra_id=obra.id)
    leitor = await leitor_factory(db_session, nome="Leitor POL FLOW-002")

    before = datetime.now(tz=timezone.utc)
    checkout_resp = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": str(exemplar.id), "leitor_id": str(leitor.id)},
        headers=auth_headers_operador,
    )
    after = datetime.now(tz=timezone.utc)

    assert checkout_resp.status_code == 201, f"Checkout falhou: {checkout_resp.text}"
    data_prevista = datetime.fromisoformat(checkout_resp.json()["data_prevista"])
    if data_prevista.tzinfo is None:
        data_prevista = data_prevista.replace(tzinfo=timezone.utc)

    # data_prevista deve ser ~now + 7d, NÃO +14d
    lower_7d = before + timedelta(days=7) - timedelta(minutes=1)
    upper_7d = after + timedelta(days=7) + timedelta(minutes=1)
    assert lower_7d <= data_prevista <= upper_7d, (
        f"data_prevista {data_prevista} deveria estar em ~now+7d "
        f"([{lower_7d}, {upper_7d}])"
    )

    # Garante que NÃO está no prazo de 14d
    lower_14d = before + timedelta(days=13)
    assert data_prevista < lower_14d, (
        f"data_prevista {data_prevista} muito longe — política de 7d não foi respeitada"
    )


# ─── FLOW-C-003 ──────────────────────────────────────────────────────────────

async def test_flow_c_003_fluxo_de_atraso(
    client: AsyncClient,
    auth_headers_operador: dict,
    db_session: AsyncSession,
) -> None:
    """
    FLOW-C-003 — Fluxo de atraso:
      Passo 1: Empréstimo com data_prevista passada (via factory)
      Passo 2: Job MarcarAtrasados marca como "atrasado"
      Passo 3: Check-in resolve a devolução
    """
    # --- Passo 1 — Empréstimo expirado ---
    obra = await obra_factory(db_session, titulo="Obra Atraso FLOW-003")
    exemplar = await exemplar_factory(
        db_session, obra_id=obra.id, codigo_qr="QR-FLOW-003-ATR", estado="emprestado"
    )
    leitor = await leitor_factory(db_session, nome="Leitor Atraso FLOW-003")
    ontem = datetime.now(timezone.utc) - timedelta(days=1)
    emprestimo = await emprestimo_factory(
        db_session,
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_prevista=ontem,
        status="ativo",
    )

    # --- Passo 2 — Job marca como atrasado ---
    use_case = MarcarAtrasadosUseCase(
        emprestimo_repo=SQLAlchemyEmprestimoRepository(db_session),
        notificacao_gateway=NotificacaoGatewayStub(),
    )
    count = await use_case.execute()
    assert count >= 1, "Job deveria ter marcado pelo menos 1 empréstimo"

    # Verifica status atrasado na listagem
    lst_resp = await client.get(
        f"/api/emprestimos?leitor_id={leitor.id}&status=atrasado",
        headers=auth_headers_operador,
    )
    assert lst_resp.status_code == 200
    items_atrasados = lst_resp.json()["items"]
    assert any(item["id"] == str(emprestimo.id) for item in items_atrasados), (
        "Empréstimo atrasado não aparece na listagem com filtro status=atrasado"
    )

    # --- Passo 3 — Check-in resolve ---
    checkin_resp = await client.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar.codigo_qr},
        headers=auth_headers_operador,
    )
    assert checkin_resp.status_code == 200, f"Check-in falhou: {checkin_resp.text}"
    assert checkin_resp.json()["status"] == "devolvido"

    # Exemplar volta a disponivel
    resp_ex = await client.get(
        f"/api/exemplares/{exemplar.id}", headers=auth_headers_operador
    )
    assert resp_ex.json()["estado"] == "disponivel"
