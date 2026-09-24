"""
Testes unitários para app/adapters/repositories/sqlalchemy_configuracao_service.py

Estratégia: usar mock do AsyncSession e verificar as queries SQL geradas,
sem banco de dados real.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app.adapters.repositories.sqlalchemy_configuracao_service import (
    ConfiguracaoServiceImpl,
)
from app.domain.services.configuracao_service import (
    CHAVE_DIAS_EMPRESTIMO,
    CHAVE_MAX_EMPRESTIMOS_POR_LEITOR,
    CHAVE_MAX_RENOVACOES,
    DEFAULT_DIAS_EMPRESTIMO,
    DEFAULT_MAX_EMPRESTIMOS_POR_LEITOR,
    DEFAULT_MAX_RENOVACOES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session() -> AsyncMock:
    """Cria um AsyncMock simulando AsyncSession do SQLAlchemy."""
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def service(mock_session: AsyncMock) -> ConfiguracaoServiceImpl:
    """Cria instância do service com session mockada."""
    return ConfiguracaoServiceImpl(mock_session)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_executed_query(mock_session: AsyncMock) -> str:
    """Extrai a query SQL executada da chamada do mock."""
    call_args = mock_session.execute.call_args
    assert call_args is not None, "session.execute não foi chamado"
    query = call_args[0][0]
    return str(query.compile(compile_kwargs={"literal_binds": True}))


# ---------------------------------------------------------------------------
# Testes do método privado _get_valor
# ---------------------------------------------------------------------------


class TestConfiguracaoServiceImplGetValor:
    @pytest.mark.asyncio
    async def test_retorna_valor_do_banco_quando_existe(
        self, service: ConfiguracaoServiceImpl, mock_session: AsyncMock
    ) -> None:
        """Quando a chave existe no banco, retorna o valor convertido para int."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "21"
        mock_session.execute.return_value = mock_result

        result = await service._get_valor(CHAVE_DIAS_EMPRESTIMO, DEFAULT_DIAS_EMPRESTIMO)

        assert result == 21
        mock_session.execute.assert_awaited_once()
        query = _get_executed_query(mock_session)
        assert "dias_emprestimo" in query
        assert "SELECT configuracao.valor" in query

    @pytest.mark.asyncio
    async def test_retorna_default_quando_chave_nao_existe(
        self, service: ConfiguracaoServiceImpl, mock_session: AsyncMock
    ) -> None:
        """Quando a chave não existe no banco, retorna o default."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service._get_valor(CHAVE_DIAS_EMPRESTIMO, DEFAULT_DIAS_EMPRESTIMO)

        assert result == DEFAULT_DIAS_EMPRESTIMO

    @pytest.mark.asyncio
    async def test_retorna_default_quando_valor_invalido(
        self, service: ConfiguracaoServiceImpl, mock_session: AsyncMock
    ) -> None:
        """Quando o valor no banco não é um inteiro válido, retorna o default."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "nao-e-um-numero"
        mock_session.execute.return_value = mock_result

        result = await service._get_valor(CHAVE_DIAS_EMPRESTIMO, DEFAULT_DIAS_EMPRESTIMO)

        assert result == DEFAULT_DIAS_EMPRESTIMO


# ---------------------------------------------------------------------------
# Testes do método dias_emprestimo
# ---------------------------------------------------------------------------


class TestConfiguracaoServiceImplDiasEmprestimo:
    @pytest.mark.asyncio
    async def test_chama_get_valor_com_chave_e_default_corretos(
        self, service: ConfiguracaoServiceImpl, mock_session: AsyncMock
    ) -> None:
        """Verifica que dias_emprestimo usa a chave e default corretos."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "30"
        mock_session.execute.return_value = mock_result

        result = await service.dias_emprestimo()

        assert result == 30
        mock_session.execute.assert_awaited_once()
        query = _get_executed_query(mock_session)
        assert "dias_emprestimo" in query

    @pytest.mark.asyncio
    async def test_retorna_default_quando_sem_configuracao(
        self, service: ConfiguracaoServiceImpl, mock_session: AsyncMock
    ) -> None:
        """Retorna DEFAULT_DIAS_EMPRESTIMO (14) quando não há config no banco."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.dias_emprestimo()

        assert result == DEFAULT_DIAS_EMPRESTIMO


# ---------------------------------------------------------------------------
# Testes do método max_renovacoes
# ---------------------------------------------------------------------------


class TestConfiguracaoServiceImplMaxRenovacoes:
    @pytest.mark.asyncio
    async def test_chama_get_valor_com_chave_e_default_corretos(
        self, service: ConfiguracaoServiceImpl, mock_session: AsyncMock
    ) -> None:
        """Verifica que max_renovacoes usa a chave e default corretos."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "5"
        mock_session.execute.return_value = mock_result

        result = await service.max_renovacoes()

        assert result == 5
        mock_session.execute.assert_awaited_once()
        query = _get_executed_query(mock_session)
        assert "max_renovacoes" in query

    @pytest.mark.asyncio
    async def test_retorna_default_quando_sem_configuracao(
        self, service: ConfiguracaoServiceImpl, mock_session: AsyncMock
    ) -> None:
        """Retorna DEFAULT_MAX_RENOVACOES (3) quando não há config no banco."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.max_renovacoes()

        assert result == DEFAULT_MAX_RENOVACOES


# ---------------------------------------------------------------------------
# Testes do método max_emprestimos_por_leitor
# ---------------------------------------------------------------------------


class TestConfiguracaoServiceImplMaxEmprestimosPorLeitor:
    @pytest.mark.asyncio
    async def test_chama_get_valor_com_chave_e_default_corretos(
        self, service: ConfiguracaoServiceImpl, mock_session: AsyncMock
    ) -> None:
        """Verifica que max_emprestimos_por_leitor usa a chave e default corretos."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "10"
        mock_session.execute.return_value = mock_result

        result = await service.max_emprestimos_por_leitor()

        assert result == 10
        mock_session.execute.assert_awaited_once()
        query = _get_executed_query(mock_session)
        assert "max_emprestimos_por_leitor" in query

    @pytest.mark.asyncio
    async def test_retorna_default_quando_sem_configuracao(
        self, service: ConfiguracaoServiceImpl, mock_session: AsyncMock
    ) -> None:
        """Retorna DEFAULT_MAX_EMPRESTIMOS_POR_LEITOR (3) quando não há config no banco."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.max_emprestimos_por_leitor()

        assert result == DEFAULT_MAX_EMPRESTIMOS_POR_LEITOR


# ---------------------------------------------------------------------------
# Testes de integração (verifica implementação da interface ABC)
# ---------------------------------------------------------------------------


class TestConfiguracaoServiceImplImplementaABC:
    def test_e_subclasse_de_configuracao_service(self) -> None:
        from app.domain.services.configuracao_service import ConfiguracaoService

        assert issubclass(ConfiguracaoServiceImpl, ConfiguracaoService)

    def test_instancia_com_session(self, mock_session: AsyncMock) -> None:
        """Construtor aceita AsyncSession e armazena internamente."""
        service = ConfiguracaoServiceImpl(mock_session)
        assert service._session is mock_session