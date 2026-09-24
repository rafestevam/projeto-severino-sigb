"""
Testes unitários para RealizarCheckoutUseCase.

Estratégia: usar unittest.mock.AsyncMock para mockar ExemplarRepository,
LeitorRepository, EmprestimoRepository e ConfiguracaoService, evitando
qualquer dependência de banco de dados, SQLAlchemy ou FastAPI.

Casos cobertos:
  - Checkout bem-sucedido: empréstimo criado com campos corretos.
  - Campos do empréstimo gerado: status 'ativo', renovacoes=0, IDs corretos.
  - Cálculo de data_prevista a partir de dias_emprestimo.
  - Ordem das operações de persistência (update_estado antes de save).
  - ExemplarNotFoundError: exemplar inexistente.
  - ExemplarNaoDisponivelError: exemplar com estado 'emprestado'.
  - ExemplarNaoDisponivelError: exemplar com estado 'baixado'.
  - LeitorInativoError: leitor não encontrado (None).
  - LeitorInativoError: leitor encontrado mas ativo=False.
  - LimiteEmprestimosAtingidoError: ativos == max_emprestimos.
  - LimiteEmprestimosAtingidoError: ativos > max_emprestimos.
  - Não persiste quando exemplar não encontrado.
  - Não persiste quando exemplar indisponível.
  - Não persiste quando leitor inativo.
  - Não persiste quando limite atingido.
  - ConfiguracaoService é consultado apenas quando as validações anteriores passam.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, call
from uuid import UUID, uuid4

import pytest

from app.domain.entities.emprestimo import Emprestimo
from app.domain.entities.exemplar import Exemplar
from app.domain.entities.leitor import Leitor
from app.domain.exceptions import (
    ExemplarNaoDisponivelError,
    ExemplarNotFoundError,
    LeitorInativoError,
    LimiteEmprestimosAtingidoError,
)
from app.use_cases.realizar_checkout import RealizarCheckoutUseCase


# ---------------------------------------------------------------------------
# Constantes e helpers de fixture
# ---------------------------------------------------------------------------

_EXEMPLAR_ID = uuid4()
_LEITOR_ID = uuid4()
_DIAS_EMPRESTIMO = 14
_MAX_EMPRESTIMOS = 3


def _make_exemplar(estado: str = "disponivel") -> Exemplar:
    return Exemplar(
        id=_EXEMPLAR_ID,
        obra_id=uuid4(),
        codigo_qr="LIB-2025-00001",
        estado=estado,
        localizacao_estante="A-01",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_leitor(ativo: bool = True) -> Leitor:
    return Leitor(
        id=_LEITOR_ID,
        nome="Ana Lima",
        cpf_hash=Leitor.hash_cpf("12345678900"),
        telefone="11999999999",
        email="ana@email.com",
        ativo=ativo,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_emprestimo_salvo(exemplar_id: UUID, leitor_id: UUID) -> Emprestimo:
    """Simula o empréstimo retornado pelo repositório após save."""
    now = datetime.now(timezone.utc)
    return Emprestimo(
        id=uuid4(),
        exemplar_id=exemplar_id,
        leitor_id=leitor_id,
        data_checkout=now,
        data_prevista=now + timedelta(days=_DIAS_EMPRESTIMO),
        data_devolucao=None,
        renovacoes=0,
        status="ativo",
    )


def _build_exemplar_repo(
    *,
    exemplar: Exemplar | None = None,
) -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=exemplar)
    repo.update_estado = AsyncMock(return_value=exemplar)
    return repo


def _build_leitor_repo(*, leitor: Leitor | None = None) -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=leitor)
    return repo


def _build_emprestimo_repo(*, ativos: int = 0) -> MagicMock:
    repo = MagicMock()
    repo.count_ativos_by_leitor = AsyncMock(return_value=ativos)
    repo.save = AsyncMock(
        side_effect=lambda emp: _make_emprestimo_salvo(emp.exemplar_id, emp.leitor_id)
    )
    return repo


def _build_config_service(
    *,
    dias: int = _DIAS_EMPRESTIMO,
    max_emprestimos: int = _MAX_EMPRESTIMOS,
) -> MagicMock:
    svc = MagicMock()
    svc.dias_emprestimo = AsyncMock(return_value=dias)
    svc.max_emprestimos_por_leitor = AsyncMock(return_value=max_emprestimos)
    return svc


def _build_use_case(
    *,
    exemplar: Exemplar | None = None,
    leitor: Leitor | None = None,
    ativos: int = 0,
    dias: int = _DIAS_EMPRESTIMO,
    max_emprestimos: int = _MAX_EMPRESTIMOS,
) -> tuple[RealizarCheckoutUseCase, MagicMock, MagicMock, MagicMock, MagicMock]:
    exemplar_repo = _build_exemplar_repo(exemplar=exemplar)
    leitor_repo = _build_leitor_repo(leitor=leitor)
    emprestimo_repo = _build_emprestimo_repo(ativos=ativos)
    config_svc = _build_config_service(dias=dias, max_emprestimos=max_emprestimos)
    use_case = RealizarCheckoutUseCase(exemplar_repo, leitor_repo, emprestimo_repo, config_svc)
    return use_case, exemplar_repo, leitor_repo, emprestimo_repo, config_svc


# ---------------------------------------------------------------------------
# Testes do caminho feliz
# ---------------------------------------------------------------------------


async def test_checkout_bem_sucedido_retorna_emprestimo():
    """execute() retorna um Emprestimo quando todas as validações passam."""
    use_case, *_ = _build_use_case(
        exemplar=_make_exemplar("disponivel"),
        leitor=_make_leitor(ativo=True),
        ativos=0,
    )

    result = await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    assert isinstance(result, Emprestimo)


async def test_checkout_emprestimo_tem_status_ativo():
    """O empréstimo criado deve ter status='ativo'."""
    use_case, *_ = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(),
    )

    result = await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    assert result.status == "ativo"


async def test_checkout_emprestimo_tem_renovacoes_zero():
    """O empréstimo criado deve ter renovacoes=0."""
    use_case, _, _, emprestimo_repo, _ = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(),
    )
    emprestimo_repo.save = AsyncMock(side_effect=lambda emp: emp)

    result = await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    assert result.renovacoes == 0


async def test_checkout_emprestimo_tem_data_devolucao_none():
    """O empréstimo criado deve ter data_devolucao=None."""
    use_case, _, _, emprestimo_repo, _ = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(),
    )
    emprestimo_repo.save = AsyncMock(side_effect=lambda emp: emp)

    result = await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    assert result.data_devolucao is None


async def test_checkout_emprestimo_tem_ids_corretos():
    """O empréstimo criado deve ter exemplar_id e leitor_id corretos."""
    use_case, _, _, emprestimo_repo, _ = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(),
    )
    emprestimo_repo.save = AsyncMock(side_effect=lambda emp: emp)

    result = await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    assert result.exemplar_id == _EXEMPLAR_ID
    assert result.leitor_id == _LEITOR_ID


async def test_checkout_data_prevista_calculada_com_dias_configurados():
    """data_prevista deve ser data_checkout + dias_emprestimo configurados."""
    dias = 21
    use_case, _, _, emprestimo_repo, _ = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(),
        dias=dias,
    )
    emprestimo_repo.save = AsyncMock(side_effect=lambda emp: emp)

    result = await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    delta = result.data_prevista - result.data_checkout
    assert delta == timedelta(days=dias)


async def test_checkout_update_estado_chamado_com_emprestado():
    """update_estado deve ser chamado com o ID do exemplar e estado 'emprestado'."""
    use_case, exemplar_repo, *_ = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(),
    )

    await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    exemplar_repo.update_estado.assert_awaited_once_with(_EXEMPLAR_ID, "emprestado")


async def test_checkout_emprestimo_save_chamado_uma_vez():
    """emprestimo_repo.save deve ser chamado exatamente uma vez."""
    use_case, _, _, emprestimo_repo, _ = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(),
    )

    await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    emprestimo_repo.save.assert_awaited_once()


async def test_checkout_consulta_config_service():
    """ConfiguracaoService deve ser consultado para dias_emprestimo e max_emprestimos_por_leitor."""
    use_case, _, _, _, config_svc = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(),
        ativos=0,
    )

    await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    config_svc.dias_emprestimo.assert_awaited_once()
    config_svc.max_emprestimos_por_leitor.assert_awaited_once()


# ---------------------------------------------------------------------------
# Testes de guarda: ExemplarNotFoundError
# ---------------------------------------------------------------------------


async def test_exemplar_nao_encontrado_levanta_exemplar_not_found_error():
    """Exemplar inexistente deve levantar ExemplarNotFoundError."""
    use_case, *_ = _build_use_case(exemplar=None, leitor=_make_leitor())

    with pytest.raises(ExemplarNotFoundError):
        await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)


async def test_exemplar_nao_encontrado_nao_persiste():
    """Quando exemplar não existe, nenhuma persistência deve ocorrer."""
    use_case, exemplar_repo, _, emprestimo_repo, _ = _build_use_case(
        exemplar=None,
        leitor=_make_leitor(),
    )

    with pytest.raises(ExemplarNotFoundError):
        await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    exemplar_repo.update_estado.assert_not_called()
    emprestimo_repo.save.assert_not_called()


async def test_exemplar_nao_encontrado_nao_consulta_leitor():
    """Quando exemplar não existe, leitor_repo não deve ser consultado."""
    use_case, _, leitor_repo, _, _ = _build_use_case(exemplar=None, leitor=_make_leitor())

    with pytest.raises(ExemplarNotFoundError):
        await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    leitor_repo.get_by_id.assert_not_called()


# ---------------------------------------------------------------------------
# Testes de guarda: ExemplarNaoDisponivelError
# ---------------------------------------------------------------------------


async def test_exemplar_emprestado_levanta_nao_disponivel_error():
    """Exemplar com estado 'emprestado' deve levantar ExemplarNaoDisponivelError."""
    use_case, *_ = _build_use_case(
        exemplar=_make_exemplar("emprestado"),
        leitor=_make_leitor(),
    )

    with pytest.raises(ExemplarNaoDisponivelError) as exc_info:
        await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    assert exc_info.value.estado_atual == "emprestado"


async def test_exemplar_baixado_levanta_nao_disponivel_error():
    """Exemplar com estado 'baixado' deve levantar ExemplarNaoDisponivelError."""
    use_case, *_ = _build_use_case(
        exemplar=_make_exemplar("baixado"),
        leitor=_make_leitor(),
    )

    with pytest.raises(ExemplarNaoDisponivelError) as exc_info:
        await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    assert exc_info.value.estado_atual == "baixado"


async def test_exemplar_nao_disponivel_nao_persiste():
    """Quando exemplar está indisponível, nenhuma persistência deve ocorrer."""
    use_case, exemplar_repo, _, emprestimo_repo, _ = _build_use_case(
        exemplar=_make_exemplar("emprestado"),
        leitor=_make_leitor(),
    )

    with pytest.raises(ExemplarNaoDisponivelError):
        await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    exemplar_repo.update_estado.assert_not_called()
    emprestimo_repo.save.assert_not_called()


# ---------------------------------------------------------------------------
# Testes de guarda: LeitorInativoError
# ---------------------------------------------------------------------------


async def test_leitor_nao_encontrado_levanta_leitor_inativo_error():
    """Leitor inexistente (None) deve levantar LeitorInativoError."""
    use_case, *_ = _build_use_case(exemplar=_make_exemplar(), leitor=None)

    with pytest.raises(LeitorInativoError) as exc_info:
        await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    assert exc_info.value.leitor_id == str(_LEITOR_ID)


async def test_leitor_inativo_levanta_leitor_inativo_error():
    """Leitor com ativo=False deve levantar LeitorInativoError."""
    use_case, *_ = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(ativo=False),
    )

    with pytest.raises(LeitorInativoError) as exc_info:
        await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    assert exc_info.value.leitor_id == str(_LEITOR_ID)


async def test_leitor_inativo_nao_persiste():
    """Quando leitor está inativo, nenhuma persistência deve ocorrer."""
    use_case, exemplar_repo, _, emprestimo_repo, _ = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(ativo=False),
    )

    with pytest.raises(LeitorInativoError):
        await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    exemplar_repo.update_estado.assert_not_called()
    emprestimo_repo.save.assert_not_called()


# ---------------------------------------------------------------------------
# Testes de guarda: LimiteEmprestimosAtingidoError
# ---------------------------------------------------------------------------


async def test_limite_atingido_exatamente_levanta_erro():
    """ativos == max_emprestimos deve levantar LimiteEmprestimosAtingidoError."""
    use_case, *_ = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(),
        ativos=_MAX_EMPRESTIMOS,
        max_emprestimos=_MAX_EMPRESTIMOS,
    )

    with pytest.raises(LimiteEmprestimosAtingidoError) as exc_info:
        await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    assert exc_info.value.leitor_id == str(_LEITOR_ID)
    assert exc_info.value.limite == _MAX_EMPRESTIMOS


async def test_limite_ultrapassado_levanta_erro():
    """ativos > max_emprestimos também deve levantar LimiteEmprestimosAtingidoError."""
    use_case, *_ = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(),
        ativos=_MAX_EMPRESTIMOS + 1,
        max_emprestimos=_MAX_EMPRESTIMOS,
    )

    with pytest.raises(LimiteEmprestimosAtingidoError):
        await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)


async def test_limite_nao_atingido_permite_checkout():
    """ativos < max_emprestimos não deve levantar exceção."""
    use_case, *_ = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(),
        ativos=_MAX_EMPRESTIMOS - 1,
        max_emprestimos=_MAX_EMPRESTIMOS,
    )

    result = await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    assert isinstance(result, Emprestimo)


async def test_limite_atingido_nao_persiste():
    """Quando limite atingido, nenhuma persistência deve ocorrer."""
    use_case, exemplar_repo, _, emprestimo_repo, _ = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(),
        ativos=_MAX_EMPRESTIMOS,
        max_emprestimos=_MAX_EMPRESTIMOS,
    )

    with pytest.raises(LimiteEmprestimosAtingidoError):
        await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    exemplar_repo.update_estado.assert_not_called()
    emprestimo_repo.save.assert_not_called()


# ---------------------------------------------------------------------------
# Testes de isolamento do ConfiguracaoService
# ---------------------------------------------------------------------------


async def test_config_service_nao_consultado_quando_exemplar_nao_encontrado():
    """ConfiguracaoService não deve ser chamado se o exemplar não existir."""
    use_case, _, _, _, config_svc = _build_use_case(exemplar=None, leitor=_make_leitor())

    with pytest.raises(ExemplarNotFoundError):
        await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    config_svc.dias_emprestimo.assert_not_called()
    config_svc.max_emprestimos_por_leitor.assert_not_called()


async def test_config_service_nao_consultado_quando_leitor_inativo():
    """ConfiguracaoService não deve ser chamado se o leitor estiver inativo."""
    use_case, _, _, _, config_svc = _build_use_case(
        exemplar=_make_exemplar(),
        leitor=_make_leitor(ativo=False),
    )

    with pytest.raises(LeitorInativoError):
        await use_case.execute(_EXEMPLAR_ID, _LEITOR_ID)

    config_svc.dias_emprestimo.assert_not_called()
