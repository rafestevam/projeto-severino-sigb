"""
Testes de integração — ST-02 Validação das Migrations Alembic (US-004).
Casos cobertos: MIG-001 a MIG-005.
"""

from __future__ import annotations

import asyncio
from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.e2e.conftest import TEST_DATABASE_URL

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

EXPECTED_TABLES = {"obra", "exemplar", "leitor", "emprestimo", "reserva", "inventario_log"}


async def _get_public_tables(conn: AsyncConnection) -> set[str]:
    """Helper para obter todas as tabelas no schema public."""
    result = await conn.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    return {row[0] for row in result.fetchall()}


def _get_alembic_config() -> Config:
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return alembic_cfg


async def test_mig_001_upgrade_head_creates_expected_tables():
    """MIG-001: upgrade head cria exatamente as 6 tabelas esperadas."""
    from tests.e2e.conftest import get_test_engine
    alembic_cfg = _get_alembic_config()
    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")

    engine = get_test_engine()
    async with engine.connect() as conn:
        tables = await _get_public_tables(conn)
    await engine.dispose()
    for expected_table in EXPECTED_TABLES:
        assert expected_table in tables, f"Tabela '{expected_table}' não encontrada após upgrade head"


async def test_mig_002_no_extra_domain_tables():
    """MIG-002: Nenhuma tabela extra de domínio é criada."""
    from tests.e2e.conftest import get_test_engine
    engine = get_test_engine()
    async with engine.connect() as conn:
        tables = await _get_public_tables(conn)
    await engine.dispose()
    # alembic_version é a tabela de controle do Alembic
    allowed_tables = EXPECTED_TABLES | {"alembic_version"}
    extra_tables = tables - allowed_tables
    assert not extra_tables, f"Tabelas inesperadas encontradas no banco: {extra_tables}"


async def test_mig_003_downgrade_minus_one_removes_circulation_tables():
    """MIG-003: downgrade -1 (de head para 0002) remove apenas as tabelas de 0003 sem erros."""
    from tests.e2e.conftest import get_test_engine
    alembic_cfg = _get_alembic_config()

    try:
        # Garante que está no head
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
        # Reverte 1 migração (0003 -> 0002)
        await asyncio.to_thread(command.downgrade, alembic_cfg, "-1")

        engine = get_test_engine()
        async with engine.connect() as conn:
            tables = await _get_public_tables(conn)
        await engine.dispose()

        # 0003 adicionou: emprestimo, reserva, inventario_log
        assert "emprestimo" not in tables
        assert "reserva" not in tables
        assert "inventario_log" not in tables

        # 0001 e 0002 devem permanecer: obra, exemplar, leitor
        assert "obra" in tables
        assert "exemplar" in tables
        assert "leitor" in tables
    finally:
        # Restaura para head
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")


async def test_mig_004_downgrade_base_removes_all_domain_tables():
    """MIG-004: downgrade base remove todas as tabelas sem erros de FK."""
    from tests.e2e.conftest import get_test_engine
    alembic_cfg = _get_alembic_config()

    try:
        # Reverte tudo para base
        await asyncio.to_thread(command.downgrade, alembic_cfg, "base")

        engine = get_test_engine()
        async with engine.connect() as conn:
            tables = await _get_public_tables(conn)
        await engine.dispose()

        for expected_table in EXPECTED_TABLES:
            assert expected_table not in tables, f"Tabela '{expected_table}' ainda existe após downgrade base"
    finally:
        # Restaura para head
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")


async def test_mig_005_upgrade_head_after_downgrade_base_is_idempotent():
    """MIG-005: Segundo upgrade head após downgrade base completa sem erros (idempotência)."""
    from tests.e2e.conftest import get_test_engine
    alembic_cfg = _get_alembic_config()

    try:
        # Reverte para base
        await asyncio.to_thread(command.downgrade, alembic_cfg, "base")
        # Aplica novamente para head
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")

        engine = get_test_engine()
        async with engine.connect() as conn:
            tables = await _get_public_tables(conn)
        await engine.dispose()

        for expected_table in EXPECTED_TABLES:
            assert expected_table in tables, f"Tabela '{expected_table}' não encontrada após re-upgrade head"
    finally:
        # Garante que continua em head
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
