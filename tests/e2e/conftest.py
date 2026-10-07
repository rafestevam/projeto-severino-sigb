"""
Fixtures de integração compartilhadas para todos os testes e2e.

Estratégia de isolamento:
- Um banco de dados de teste dedicado (DATABASE_URL_TEST) é criado antes da sessão
  e destruído ao final — nunca o banco de produção/desenvolvimento é tocado.
- Cada *test function* recebe uma transação aninhada (SAVEPOINT) que é revertida ao
  término do teste, mantendo o schema limpo sem re-executar as migrations a cada caso.
- A instância FastAPI + httpx.AsyncClient é criada uma vez por sessão de pytest.

Variáveis de ambiente esperadas (padrão para execução local via Docker Compose):
  DATABASE_URL_TEST=postgresql+asyncpg://libsys:changeme@localhost:5432/libsysdb_test
  DATABASE_URL      (usada como base para criar o banco de teste se TEST não estiver set)

Para executar apenas os testes de integração:
  pytest -m integration tests/e2e/
"""

from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ─── URL do banco de testes ───────────────────────────────────────────────────
# Usa DATABASE_URL_TEST se definida; senão deriva do DATABASE_URL substituindo o
# nome do banco por libsysdb_test.
_default_url = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://libsys:changeme@localhost:5432/libsysdb"
)
TEST_DATABASE_URL: str = os.environ.get(
    "DATABASE_URL_TEST",
    _default_url.rsplit("/", 1)[0] + "/libsysdb_test",
)

# ─── Engine e sessionmaker de teste ──────────────────────────────────────────
def get_test_engine():
    from sqlalchemy.pool import NullPool
    return create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)


# ─── Setup do schema (uma vez por sessão pytest) ─────────────────────────────
@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_test_schema():
    """
    Aplica todas as migrations Alembic no banco de teste uma única vez por sessão.
    Ao final derruba o schema completo.

    Requer que o banco libsysdb_test já exista (criado pelo DBA ou pelo CI).
    Em desenvolvimento local: `createdb -U libsys libsysdb_test`
    """
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    # Aplica migrations de forma síncrona (Alembic não é async-nativo)
    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")

    yield

    # Teardown: reverte tudo para deixar o banco limpo para a próxima execução
    await asyncio.to_thread(command.downgrade, alembic_cfg, "base")


# ─── Fixture de conexão com rollback por teste ───────────────────────────────
@pytest_asyncio.fixture()
async def db_connection() -> AsyncGenerator[AsyncConnection, None]:
    """
    Abre uma conexão e inicia um SAVEPOINT/transação antes de cada teste.
    O rollback ao final garante isolamento total sem re-criar o schema.
    """
    engine = get_test_engine()
    async with engine.connect() as conn:
        trans = await conn.begin()  # outer transaction
        try:
            nested = await conn.begin_nested()
            yield conn
        finally:
            if nested.is_active:
                await nested.rollback()
            if trans.is_active:
                await trans.rollback()
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(db_connection: AsyncConnection) -> AsyncGenerator[AsyncSession, None]:
    """
    AsyncSession ligada à conexão transacional do teste (com rollback garantido).
    Use esta fixture nos testes que precisam de acesso direto ao banco.
    """
    session = AsyncSession(bind=db_connection, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()


# ─── HTTP client ─────────────────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def client(db_connection: AsyncConnection) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient do httpx apontando para a app FastAPI em modo ASGI.

    A sessão de banco injetada na app é a mesma conexão transacional do teste,
    garantindo que os dados criados via HTTP sejam visíveis nas asserções e
    revertidos ao fim do teste.

    Quando a app ainda não tiver os routers implementados, o cliente simplesmente
    não encontrará as rotas — os testes falharão com 404/422, o que é o
    comportamento correto de um teste de integração pendente.
    """
    from app.main import app

    # Sobrescreve o gerador de sessão da app para usar a conexão do teste
    try:
        from app.infrastructure.database import get_db_session  # noqa: F401 — importação opcional

        async def _override_get_db():
            # Cria sessão vinculada à conexão transacional do teste.
            # commit() libera o sub-savepoint criado pelo autobegin da sessão,
            # tornando as escritas visíveis para db_session (na mesma conexão/SAVEPOINT).
            # rollback() desfaz em caso de erro de integridade no handler HTTP.
            session = AsyncSession(bind=db_connection, expire_on_commit=False)
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

        app.dependency_overrides[get_db_session] = _override_get_db  # type: ignore[attr-defined]
    except ImportError:
        # get_db_session ainda não foi implementado — testes funcionarão quando a ST for
        # implementada; por ora o override não é aplicado.
        pass

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


# ─── Fixture de autenticação simulada ─────────────────────────────────────────
@pytest.fixture()
def auth_headers_operador() -> dict[str, str]:
    """
    Cabeçalhos HTTP com token Bearer simulado para o perfil `operador`.
    Substituir pelo token real quando o middleware JWT (US-003) for implementado.
    """
    return {"Authorization": "Bearer test-token-operador"}


@pytest.fixture()
def auth_headers_admin() -> dict[str, str]:
    """
    Cabeçalhos HTTP com token Bearer simulado para o perfil `admin`.
    Substituir pelo token real quando o middleware JWT (US-003) for implementado.
    """
    return {"Authorization": "Bearer test-token-admin"}
