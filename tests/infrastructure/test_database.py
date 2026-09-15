"""
Testes unitários mockados para app/infrastructure/database.py.

O módulo usa lazy initialization: `create_async_engine` e `async_sessionmaker`
são chamados na primeira vez que o engine/sessionmaker é acessado, não no import.
Os testes acionam essa inicialização acessando atributos dos proxies dentro do
bloco de patch, garantindo que nenhuma conexão real de banco seja aberta.
"""
from __future__ import annotations

import importlib
from unittest.mock import MagicMock, call, patch

import pytest

# Import feito uma única vez, fora de qualquer patch, para que o módulo já
# esteja no cache de `sys.modules`. Assim, todo `importlib.reload` dentro dos
# testes executa o corpo do módulo exatamente uma vez (dentro do patch ativo).
import app.infrastructure.database as database_module


def _reload_database_module():
    return importlib.reload(database_module)


@pytest.fixture(autouse=True)
def _restore_real_database_module():
    """Recarrega o módulo com as dependências reais após cada teste, para
    que nenhum estado mockado escape para outros testes/módulos."""
    yield
    _reload_database_module()


class TestDatabaseUrlResolution:
    def test_usa_url_padrao_quando_variavel_de_ambiente_nao_definida(self, monkeypatch) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_create_engine, \
             patch("sqlalchemy.ext.asyncio.async_sessionmaker"):
            mock_create_engine.return_value = MagicMock(name="async_engine")
            database = _reload_database_module()

            expected_url = "postgresql+asyncpg://libsys:changeme@db:5432/libsysdb"
            assert database.DATABASE_URL == expected_url

            # Trigger lazy init by accessing an attribute of the proxy
            _ = database.async_engine.url
            mock_create_engine.assert_called_once_with(expected_url)

    def test_usa_url_da_variavel_de_ambiente_quando_definida(self, monkeypatch) -> None:
        custom_url = "postgresql+asyncpg://custom:pw@customhost:5432/customdb"
        monkeypatch.setenv("DATABASE_URL", custom_url)

        with patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_create_engine, \
             patch("sqlalchemy.ext.asyncio.async_sessionmaker"):
            mock_create_engine.return_value = MagicMock(name="async_engine")
            database = _reload_database_module()

            assert database.DATABASE_URL == custom_url

            # Trigger lazy init
            _ = database.async_engine.url
            mock_create_engine.assert_called_once_with(custom_url)


class TestAsyncSessionLocal:
    def test_sessionmaker_e_construido_a_partir_do_engine_criado(self, monkeypatch) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        fake_engine = MagicMock(name="async_engine")
        fake_session_local = MagicMock(name="AsyncSessionLocal")

        with patch(
            "sqlalchemy.ext.asyncio.create_async_engine", return_value=fake_engine
        ) as mock_create_engine, patch(
            "sqlalchemy.ext.asyncio.async_sessionmaker", return_value=fake_session_local
        ) as mock_sessionmaker:
            database = _reload_database_module()

            # Trigger lazy init of both engine and sessionmaker
            _ = database.async_engine.url
            _ = database.AsyncSessionLocal.kw

            mock_create_engine.assert_called_once()
            mock_sessionmaker.assert_called_once_with(
                bind=fake_engine, class_=database.AsyncSession, expire_on_commit=False
            )


class TestBase:
    def test_base_e_subclasse_de_declarative_base(self) -> None:
        from sqlalchemy.orm import DeclarativeBase

        from app.infrastructure.database import Base

        assert issubclass(Base, DeclarativeBase)
