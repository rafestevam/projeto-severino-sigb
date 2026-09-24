"""
Testes unitários para RenovarEmprestimoUseCase.

Estratégia: usar unittest.mock.AsyncMock para mockar EmprestimoRepository
e ConfiguracaoService, sem dependência de banco de dados, SQLAlchemy ou FastAPI.

Casos cobertos:
  - Renovação bem-sucedida: empréstimo atualizado com renovacoes incrementadas.
  - Recálculo de data_prevista a partir do momento atual + dias_emprestimo.
  - Preservação dos demais campos (id, exemplar_id, leitor_id, data_checkout, status).
  - EmprestimoNaoEncontradoError: empréstimo inexistente (None).
  - LimiteRenovacoesAtingidoError: renovacoes == max_renovacoes.
  - LimiteRenovacoesAtingidoError: renovacoes > max_renovacoes.
  - Não persiste quando empréstimo não encontrado.
  - Não persiste quando limite de renovações atingido.
  - ConfiguracaoService não consulta dias_emprestimo se limite for atingido.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.domain.entities.emprestimo import Emprestimo
from app.domain.exceptions import (
    EmprestimoNaoEncontradoError,
    LimiteRenovacoesAtingidoError,
)
from app.use_cases.renovar_emprestimo import RenovarEmprestimoUseCase


# ---------------------------------------------------------------------------
# Constantes e helpers de fixture
# ---------------------------------------------------------------------------

_EMPRESTIMO_ID = uuid4()
_EXEMPLAR_ID = uuid4()
_LEITOR_ID = uuid4()
_DIAS_EMPRESTIMO = 14
_MAX_RENOVACOES = 3


def _make_emprestimo(
    *,
    id: UUID = _EMPRESTIMO_ID,
    renovacoes: int = 0,
    status: str = "ativo",
    data_checkout: datetime | None = None,
    data_prevista: datetime | None = None,
) -> Emprestimo:
    now = datetime.now(timezone.utc)
    checkout = data_checkout or (now - timedelta(days=10))
    prevista = data_prevista or (checkout + timedelta(days=_DIAS_EMPRESTIMO))
    return Emprestimo(
        id=id,
        exemplar_id=_EXEMPLAR_ID,
        leitor_id=_LEITOR_ID,
        data_checkout=checkout,
        data_prevista=prevista,
        data_devolucao=None,
        renovacoes=renovacoes,
        status=status,  # type: ignore[arg-type]
    )


def _build_emprestimo_repo(*, emprestimo: Emprestimo | None = None) -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=emprestimo)
    repo.save = AsyncMock(side_effect=lambda emp: emp)
    return repo


def _build_config_service(
    *,
    dias: int = _DIAS_EMPRESTIMO,
    max_renovacoes: int = _MAX_RENOVACOES,
) -> MagicMock:
    svc = MagicMock()
    svc.dias_emprestimo = AsyncMock(return_value=dias)
    svc.max_renovacoes = AsyncMock(return_value=max_renovacoes)
    return svc


def _build_use_case(
    *,
    emprestimo: Emprestimo | None = None,
    dias: int = _DIAS_EMPRESTIMO,
    max_renovacoes: int = _MAX_RENOVACOES,
) -> tuple[RenovarEmprestimoUseCase, MagicMock, MagicMock]:
    emprestimo_repo = _build_emprestimo_repo(emprestimo=emprestimo)
    config_svc = _build_config_service(dias=dias, max_renovacoes=max_renovacoes)
    use_case = RenovarEmprestimoUseCase(emprestimo_repo, config_svc)
    return use_case, emprestimo_repo, config_svc


# ---------------------------------------------------------------------------
# Testes do caminho feliz
# ---------------------------------------------------------------------------


async def test_renovacao_bem_sucedida_retorna_emprestimo():
    """execute() retorna um Emprestimo com sucesso."""
    emp = _make_emprestimo(renovacoes=0)
    use_case, *_ = _build_use_case(emprestimo=emp)

    result = await use_case.execute(_EMPRESTIMO_ID)

    assert isinstance(result, Emprestimo)


async def test_renovacao_incrementa_contador():
    """renovacoes deve ser incrementado em 1."""
    emp = _make_emprestimo(renovacoes=1)
    use_case, *_ = _build_use_case(emprestimo=emp)

    result = await use_case.execute(_EMPRESTIMO_ID)

    assert result.renovacoes == 2


async def test_renovacao_recalcula_data_prevista():
    """data_prevista deve ser recalculada a partir do momento da renovação + dias_emprestimo."""
    dias = 20
    emp = _make_emprestimo(renovacoes=0)
    use_case, _, config_svc = _build_use_case(emprestimo=emp, dias=dias)

    before = datetime.now(timezone.utc)
    result = await use_case.execute(_EMPRESTIMO_ID)
    after = datetime.now(timezone.utc)

    assert before + timedelta(days=dias) <= result.data_prevista <= after + timedelta(days=dias)


async def test_renovacao_persiste_via_save():
    """emprestimo_repo.save deve ser chamado uma vez com o empréstimo atualizado."""
    emp = _make_emprestimo(renovacoes=0)
    use_case, emprestimo_repo, _ = _build_use_case(emprestimo=emp)

    await use_case.execute(_EMPRESTIMO_ID)

    emprestimo_repo.save.assert_awaited_once_with(emp)


async def test_renovacao_preserva_campos_imutaveis():
    """Campos como id, exemplar_id, leitor_id, data_checkout e status devem ser preservados."""
    checkout = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    emp = _make_emprestimo(
        id=_EMPRESTIMO_ID,
        renovacoes=0,
        status="ativo",
        data_checkout=checkout,
    )
    use_case, *_ = _build_use_case(emprestimo=emp)

    result = await use_case.execute(_EMPRESTIMO_ID)

    assert result.id == _EMPRESTIMO_ID
    assert result.exemplar_id == _EXEMPLAR_ID
    assert result.leitor_id == _LEITOR_ID
    assert result.data_checkout == checkout
    assert result.status == "ativo"
    assert result.data_devolucao is None


async def test_renovacao_permite_quando_renovacoes_menor_que_limite():
    """Renovação deve ocorrer com sucesso quando renovacoes < max_renovacoes."""
    emp = _make_emprestimo(renovacoes=_MAX_RENOVACOES - 1)
    use_case, *_ = _build_use_case(emprestimo=emp, max_renovacoes=_MAX_RENOVACOES)

    result = await use_case.execute(_EMPRESTIMO_ID)

    assert result.renovacoes == _MAX_RENOVACOES


# ---------------------------------------------------------------------------
# Testes de guarda: EmprestimoNaoEncontradoError
# ---------------------------------------------------------------------------


async def test_emprestimo_nao_encontrado_levanta_erro():
    """Empréstimo inexistente deve levantar EmprestimoNaoEncontradoError."""
    use_case, *_ = _build_use_case(emprestimo=None)

    with pytest.raises(EmprestimoNaoEncontradoError) as exc_info:
        await use_case.execute(_EMPRESTIMO_ID)

    assert exc_info.value.identifier == str(_EMPRESTIMO_ID)


async def test_emprestimo_nao_encontrado_nao_persiste():
    """Quando empréstimo não existe, repo.save não deve ser chamado."""
    use_case, emprestimo_repo, _ = _build_use_case(emprestimo=None)

    with pytest.raises(EmprestimoNaoEncontradoError):
        await use_case.execute(_EMPRESTIMO_ID)

    emprestimo_repo.save.assert_not_called()


async def test_emprestimo_nao_encontrado_nao_consulta_config_service():
    """Quando empréstimo não existe, ConfiguracaoService não deve ser consultado."""
    use_case, _, config_svc = _build_use_case(emprestimo=None)

    with pytest.raises(EmprestimoNaoEncontradoError):
        await use_case.execute(_EMPRESTIMO_ID)

    config_svc.max_renovacoes.assert_not_called()
    config_svc.dias_emprestimo.assert_not_called()


# ---------------------------------------------------------------------------
# Testes de guarda: LimiteRenovacoesAtingidoError
# ---------------------------------------------------------------------------


async def test_limite_renovacoes_atingido_exatamente_levanta_erro():
    """renovacoes == max_renovacoes deve levantar LimiteRenovacoesAtingidoError."""
    emp = _make_emprestimo(renovacoes=_MAX_RENOVACOES)
    use_case, *_ = _build_use_case(emprestimo=emp, max_renovacoes=_MAX_RENOVACOES)

    with pytest.raises(LimiteRenovacoesAtingidoError) as exc_info:
        await use_case.execute(_EMPRESTIMO_ID)

    assert exc_info.value.emprestimo_id == str(_EMPRESTIMO_ID)
    assert exc_info.value.limite == _MAX_RENOVACOES


async def test_limite_renovacoes_ultrapassado_levanta_erro():
    """renovacoes > max_renovacoes deve levantar LimiteRenovacoesAtingidoError."""
    emp = _make_emprestimo(renovacoes=_MAX_RENOVACOES + 1)
    use_case, *_ = _build_use_case(emprestimo=emp, max_renovacoes=_MAX_RENOVACOES)

    with pytest.raises(LimiteRenovacoesAtingidoError):
        await use_case.execute(_EMPRESTIMO_ID)


async def test_limite_renovacoes_atingido_nao_persiste():
    """Quando limite atingido, repo.save não deve ser chamado."""
    emp = _make_emprestimo(renovacoes=_MAX_RENOVACOES)
    use_case, emprestimo_repo, _ = _build_use_case(emprestimo=emp, max_renovacoes=_MAX_RENOVACOES)

    with pytest.raises(LimiteRenovacoesAtingidoError):
        await use_case.execute(_EMPRESTIMO_ID)

    emprestimo_repo.save.assert_not_called()


async def test_limite_renovacoes_atingido_nao_consulta_dias_emprestimo():
    """ConfiguracaoService.dias_emprestimo não deve ser chamado se limite atingido."""
    emp = _make_emprestimo(renovacoes=_MAX_RENOVACOES)
    use_case, _, config_svc = _build_use_case(emprestimo=emp, max_renovacoes=_MAX_RENOVACOES)

    with pytest.raises(LimiteRenovacoesAtingidoError):
        await use_case.execute(_EMPRESTIMO_ID)

    config_svc.dias_emprestimo.assert_not_called()
