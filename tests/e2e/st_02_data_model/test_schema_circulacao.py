"""
Testes de integração — ST-02 Validação do Schema: Empréstimo, Reserva e InventárioLog (US-007).
Casos cobertos: EMP-001 a EMP-008, RES-001 a RES-005, INV-001 a INV-005.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.adapters.repositories.models.emprestimo import EmprestimoModel
from app.adapters.repositories.models.exemplar import ExemplarModel
from app.adapters.repositories.models.inventario_log import InventarioLogModel
from app.adapters.repositories.models.leitor import LeitorModel
from app.adapters.repositories.models.obra import ObraModel
from app.adapters.repositories.models.reserva import ReservaModel
from app.domain.entities.leitor import Leitor

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def _create_obra_exemplar_leitor(db_session: AsyncSession):
    now = datetime.now(timezone.utc)
    obra = ObraModel(
        id=uuid.uuid4(),
        isbn=f"9788500{uuid.uuid4().hex[:6]}",
        titulo="Obra Base Teste Circulacao",
        autores=["Autor Base"],
        editora="Editora Base",
        ano=2024,
        categoria="Literatura",
        capa_url=None,
    )
    db_session.add(obra)
    await db_session.flush()

    exemplar = ExemplarModel(
        id=uuid.uuid4(),
        obra_id=obra.id,
        codigo_qr=f"LIB-CIRC-{uuid.uuid4().hex[:6]}",
        estado="disponivel",
        localizacao_estante="E1-P1",
    )
    leitor = LeitorModel(
        id=uuid.uuid4(),
        nome="Leitor Circulacao",
        cpf_hash=Leitor.hash_cpf(f"123{uuid.uuid4().int % 100000000:08d}"),
        telefone="11988887777",
        email=f"leitor_{uuid.uuid4().hex[:4]}@example.com",
        ativo=True,
    )
    db_session.add_all([exemplar, leitor])
    await db_session.flush()
    return obra, exemplar, leitor


# ─── EMPRESTIMO (EMP-001 a EMP-008) ──────────────────────────────────────────

async def test_emp_001_insert_valid_emprestimo(db_session: AsyncSession):
    """EMP-001: Inserir empréstimo com exemplar e leitor válidos persiste corretamente."""
    obra, exemplar, leitor = await _create_obra_exemplar_leitor(db_session)
    now = datetime.now(timezone.utc)

    emprestimo = EmprestimoModel(
        id=uuid.uuid4(),
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_checkout=now,
        data_prevista=now + timedelta(days=14),
        data_devolucao=None,
        renovacoes=0,
        status="ativo",
    )
    db_session.add(emprestimo)
    await db_session.flush()

    saved = await db_session.get(EmprestimoModel, emprestimo.id)
    assert saved is not None
    assert saved.exemplar_id == exemplar.id
    assert saved.leitor_id == leitor.id
    assert saved.status == "ativo"


async def test_emp_002_data_devolucao_nullable(db_session: AsyncSession):
    """EMP-002: Empréstimo com data_devolucao = NULL é inserido sem erro."""
    obra, exemplar, leitor = await _create_obra_exemplar_leitor(db_session)
    now = datetime.now(timezone.utc)

    emprestimo = EmprestimoModel(
        id=uuid.uuid4(),
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_checkout=now,
        data_prevista=now + timedelta(days=14),
        data_devolucao=None,
        renovacoes=0,
        status="ativo",
    )
    db_session.add(emprestimo)
    await db_session.flush()

    saved = await db_session.get(EmprestimoModel, emprestimo.id)
    assert saved is not None
    assert saved.data_devolucao is None


@pytest.mark.parametrize("status_valido", ["ativo", "devolvido", "atrasado"])
async def test_emp_003_004_005_status_enum(db_session: AsyncSession, status_valido: str):
    """EMP-003, EMP-004, EMP-005: Empréstimo com status 'ativo', 'devolvido', 'atrasado' é aceito."""
    obra, exemplar, leitor = await _create_obra_exemplar_leitor(db_session)
    now = datetime.now(timezone.utc)

    emprestimo = EmprestimoModel(
        id=uuid.uuid4(),
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_checkout=now - timedelta(days=5),
        data_prevista=now + timedelta(days=5),
        data_devolucao=now if status_valido == "devolvido" else None,
        renovacoes=0,
        status=status_valido,
    )
    db_session.add(emprestimo)
    await db_session.flush()

    saved = await db_session.get(EmprestimoModel, emprestimo.id)
    assert saved is not None
    assert saved.status == status_valido


async def test_emp_006_invalid_exemplar_id_raises_integrity_error(db_session: AsyncSession):
    """EMP-006: Empréstimo com exemplar_id inexistente lança IntegrityError."""
    _, _, leitor = await _create_obra_exemplar_leitor(db_session)
    now = datetime.now(timezone.utc)

    emprestimo = EmprestimoModel(
        id=uuid.uuid4(),
        exemplar_id=uuid.uuid4(),  # não existente
        leitor_id=leitor.id,
        data_checkout=now,
        data_prevista=now + timedelta(days=14),
        data_devolucao=None,
        renovacoes=0,
        status="ativo",
    )
    db_session.add(emprestimo)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_emp_007_invalid_leitor_id_raises_integrity_error(db_session: AsyncSession):
    """EMP-007: Empréstimo com leitor_id inexistente lança IntegrityError."""
    _, exemplar, _ = await _create_obra_exemplar_leitor(db_session)
    now = datetime.now(timezone.utc)

    emprestimo = EmprestimoModel(
        id=uuid.uuid4(),
        exemplar_id=exemplar.id,
        leitor_id=uuid.uuid4(),  # não existente
        data_checkout=now,
        data_prevista=now + timedelta(days=14),
        data_devolucao=None,
        renovacoes=0,
        status="ativo",
    )
    db_session.add(emprestimo)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_emp_008_emprestimo_preserved_after_exemplar_baixado(db_session: AsyncSession):
    """EMP-008: Registros de empréstimo existem após mudar estado do exemplar para 'baixado'."""
    obra, exemplar, leitor = await _create_obra_exemplar_leitor(db_session)
    now = datetime.now(timezone.utc)

    # Exemplar passa para emprestado
    exemplar.estado = "emprestado"
    await db_session.flush()

    emprestimo = EmprestimoModel(
        id=uuid.uuid4(),
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_checkout=now,
        data_prevista=now + timedelta(days=14),
        data_devolucao=None,
        renovacoes=0,
        status="ativo",
    )
    db_session.add(emprestimo)
    await db_session.flush()

    # Muda o estado do exemplar para baixado
    exemplar.estado = "baixado"
    await db_session.flush()

    # O empréstimo ainda existe e continua apontando para o exemplar
    saved_emp = await db_session.get(EmprestimoModel, emprestimo.id)
    assert saved_emp is not None
    assert saved_emp.exemplar_id == exemplar.id

    saved_exp = await db_session.get(ExemplarModel, exemplar.id)
    assert saved_exp is not None
    assert saved_exp.estado == "baixado"


# ─── RESERVA (RES-001 a RES-005) ─────────────────────────────────────────────

async def test_res_001_reserva_references_obra_not_exemplar(
    db_session: AsyncSession, db_connection: AsyncConnection
):
    """RES-001: Inserir reserva referenciando obra_id (não exemplar_id) persiste corretamente."""
    obra, _, leitor = await _create_obra_exemplar_leitor(db_session)

    reserva = ReservaModel(
        id=uuid.uuid4(),
        obra_id=obra.id,
        leitor_id=leitor.id,
        status="aguardando",
    )
    db_session.add(reserva)
    await db_session.flush()

    saved = await db_session.get(ReservaModel, reserva.id)
    assert saved is not None
    assert saved.obra_id == obra.id
    assert saved.leitor_id == leitor.id

    # Verifica se tabela reserva não possui coluna exemplar_id
    result = await db_connection.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name = 'reserva'")
    )
    columns = {row[0] for row in result.fetchall()}
    assert "exemplar_id" not in columns, "Tabela reserva não deve conter coluna exemplar_id"
    assert "obra_id" in columns, "Tabela reserva deve conter coluna obra_id"


@pytest.mark.parametrize("status_reserva", ["aguardando", "disponivel", "expirada", "atendida"])
async def test_res_002_to_005_status_enum(db_session: AsyncSession, status_reserva: str):
    """RES-002 a RES-005: Reserva com status 'aguardando', 'disponivel', 'expirada', 'atendida' é aceita."""
    obra, _, leitor = await _create_obra_exemplar_leitor(db_session)

    reserva = ReservaModel(
        id=uuid.uuid4(),
        obra_id=obra.id,
        leitor_id=leitor.id,
        status=status_reserva,
    )
    db_session.add(reserva)
    await db_session.flush()

    saved = await db_session.get(ReservaModel, reserva.id)
    assert saved is not None
    assert saved.status == status_reserva


# ─── INVENTARIO_LOG (INV-001 a INV-005) ──────────────────────────────────────

async def test_inv_001_insert_inventario_log_valid_exemplar(db_session: AsyncSession):
    """INV-001: Inserir inventario_log com exemplar_id válido persiste corretamente."""
    _, exemplar, _ = await _create_obra_exemplar_leitor(db_session)

    log = InventarioLogModel(
        id=uuid.uuid4(),
        exemplar_id=exemplar.id,
        operador_keycloak_id="auth0|user-12345",
        acao="encontrado",
    )
    db_session.add(log)
    await db_session.flush()

    saved = await db_session.get(InventarioLogModel, log.id)
    assert saved is not None
    assert saved.exemplar_id == exemplar.id
    assert saved.operador_keycloak_id == "auth0|user-12345"
    assert saved.acao == "encontrado"


async def test_inv_002_operador_keycloak_id_free_string(
    db_session: AsyncSession, db_connection: AsyncConnection
):
    """INV-002: operador_keycloak_id é armazenado como string UUID sem FK."""
    _, exemplar, _ = await _create_obra_exemplar_leitor(db_session)
    random_keycloak_id = str(uuid.uuid4())

    log = InventarioLogModel(
        id=uuid.uuid4(),
        exemplar_id=exemplar.id,
        operador_keycloak_id=random_keycloak_id,
        acao="falta",
    )
    db_session.add(log)
    await db_session.flush()

    saved = await db_session.get(InventarioLogModel, log.id)
    assert saved is not None
    assert saved.operador_keycloak_id == random_keycloak_id

    # Verifica que não há FK constraint no operador_keycloak_id
    result = await db_connection.execute(
        text(
            "SELECT tc.constraint_name, kcu.column_name "
            "FROM information_schema.table_constraints AS tc "
            "JOIN information_schema.key_column_usage AS kcu "
            "  ON tc.constraint_name = kcu.constraint_name "
            "WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = 'inventario_log'"
        )
    )
    fks = result.fetchall()
    fk_cols = [row[1] for row in fks]
    assert "operador_keycloak_id" not in fk_cols, "operador_keycloak_id não deve ter chave estrangeira"
    assert "exemplar_id" in fk_cols, "exemplar_id deve ter chave estrangeira"


@pytest.mark.parametrize("acao_valida", ["encontrado", "falta", "baixado"])
async def test_inv_003_004_005_acoes_enum(db_session: AsyncSession, acao_valida: str):
    """INV-003, INV-004, INV-005: acao 'encontrado', 'falta', 'baixado' é aceita."""
    _, exemplar, _ = await _create_obra_exemplar_leitor(db_session)

    log = InventarioLogModel(
        id=uuid.uuid4(),
        exemplar_id=exemplar.id,
        operador_keycloak_id="operador-test",
        acao=acao_valida,
    )
    db_session.add(log)
    await db_session.flush()

    saved = await db_session.get(InventarioLogModel, log.id)
    assert saved is not None
    assert saved.acao == acao_valida
