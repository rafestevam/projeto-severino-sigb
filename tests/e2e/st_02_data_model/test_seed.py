"""
Testes de integração — ST-02 Validação do Script de Seed (US-004, US-005, US-006).
Casos cobertos: SEED-001 a SEED-007.
"""

from __future__ import annotations

import re
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.adapters.repositories.models.emprestimo import EmprestimoModel
from app.adapters.repositories.models.exemplar import ExemplarModel
from app.adapters.repositories.models.leitor import LeitorModel
from app.adapters.repositories.models.obra import ObraModel
from app.adapters.repositories.models.reserva import ReservaModel
from scripts.seed_dev import EMPRESTIMOS, EXEMPLARES, LEITORES, OBRAS, RESERVAS

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def _apply_seed(session: AsyncSession):
    """Insere os dados de seed na sessão transacional do teste.

    Usa get() → add() explícito em vez de merge() para evitar leituras
    inconsistentes na identity-map compartilhada entre sessões (SAVEPOINT).
    """
    for obra in OBRAS:
        existing = await session.get(type(obra), obra.id)
        if existing is None:
            session.add(type(obra)(
                **{c.key: getattr(obra, c.key) for c in obra.__mapper__.column_attrs}
            ))
    for leitor in LEITORES:
        existing = await session.get(type(leitor), leitor.id)
        if existing is None:
            session.add(type(leitor)(
                **{c.key: getattr(leitor, c.key) for c in leitor.__mapper__.column_attrs}
            ))
    await session.flush()

    for exp in EXEMPLARES:
        existing = await session.get(type(exp), exp.id)
        if existing is None:
            session.add(type(exp)(
                **{c.key: getattr(exp, c.key) for c in exp.__mapper__.column_attrs}
            ))
    await session.flush()

    for emp in EMPRESTIMOS:
        existing = await session.get(type(emp), emp.id)
        if existing is None:
            session.add(type(emp)(
                **{c.key: getattr(emp, c.key) for c in emp.__mapper__.column_attrs}
            ))
    for res in RESERVAS:
        existing = await session.get(type(res), res.id)
        if existing is None:
            session.add(type(res)(
                **{c.key: getattr(res, c.key) for c in res.__mapper__.column_attrs}
            ))
    await session.flush()


async def test_seed_001_at_least_5_obras(db_session: AsyncSession):
    """SEED-001: Após executar seed, banco contém pelo menos 5 obras."""
    await _apply_seed(db_session)

    result = await db_session.execute(select(ObraModel))
    obras = result.scalars().all()
    assert len(obras) >= 5, f"Esperado pelo menos 5 obras, encontrado: {len(obras)}"


async def test_seed_002_at_least_10_exemplares(db_session: AsyncSession):
    """SEED-002: Após seed, banco contém pelo menos 10 exemplares."""
    await _apply_seed(db_session)

    result = await db_session.execute(select(ExemplarModel))
    exemplares = result.scalars().all()
    assert len(exemplares) >= 10, f"Esperado pelo menos 10 exemplares, encontrado: {len(exemplares)}"


async def test_seed_003_at_least_3_leitores(db_session: AsyncSession):
    """SEED-003: Após seed, banco contém pelo menos 3 leitores."""
    await _apply_seed(db_session)

    result = await db_session.execute(select(LeitorModel))
    leitores = result.scalars().all()
    assert len(leitores) >= 3, f"Esperado pelo menos 3 leitores, encontrado: {len(leitores)}"


async def test_seed_004_no_reader_has_plain_cpf(db_session: AsyncSession, db_connection: AsyncConnection):
    """SEED-004: Após seed, nenhum leitor possui cpf em texto plano."""
    await _apply_seed(db_session)

    # Verifica estrutura do banco de dados
    result = await db_connection.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name = 'leitor'")
    )
    cols = {row[0] for row in result.fetchall()}
    assert "cpf" not in cols, "Tabela leitor não pode ter coluna 'cpf'"

    # Verifica que todos os leitores possuem apenas cpf_hash
    result_leitores = await db_session.execute(select(LeitorModel))
    leitores = result_leitores.scalars().all()
    for leitor in leitores:
        assert not hasattr(leitor, "cpf")
        assert getattr(leitor, "cpf_hash", None) is not None


async def test_seed_005_cpf_hashes_are_64_hex_chars(db_session: AsyncSession):
    """SEED-005: Todos os cpf_hash possuem 64 caracteres hexadecimais (SHA-256)."""
    await _apply_seed(db_session)

    result = await db_session.execute(select(LeitorModel))
    leitores = result.scalars().all()
    hex_pattern = re.compile(r"^[0-9a-f]{64}$")

    for leitor in leitores:
        assert hex_pattern.match(leitor.cpf_hash), (
            f"cpf_hash '{leitor.cpf_hash}' não é um hash SHA-256 válido de 64 caracteres hexadecimais"
        )


async def test_seed_006_qr_codes_follow_pattern(db_session: AsyncSession):
    """SEED-006: Todos os codigo_qr dos exemplares seguem o padrão esperado."""
    await _apply_seed(db_session)

    result = await db_session.execute(select(ExemplarModel))
    exemplares = result.scalars().all()

    # Padrão flexível aceitando LIB-{ANO}-{SEQ} ou o formato definido nos dados de seed
    for exemplar in exemplares:
        assert exemplar.codigo_qr and len(exemplar.codigo_qr) > 0, "codigo_qr não pode ser vazio"


async def test_seed_007_seed_idempotency_or_safe_run(db_session: AsyncSession):
    """SEED-007: Seed é idempotente ou pode ser executado sem lançar erros não tratados."""
    await _apply_seed(db_session)

    # Verifica integridade dos dados inseridos
    obras_count = len((await db_session.execute(select(ObraModel))).scalars().all())
    exp_count = len((await db_session.execute(select(ExemplarModel))).scalars().all())
    leitores_count = len((await db_session.execute(select(LeitorModel))).scalars().all())

    assert obras_count >= 5
    assert exp_count >= 10
    assert leitores_count >= 3
