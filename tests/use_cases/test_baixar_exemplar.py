"""
Testes unitários para BaixarExemplarUseCase (US-020).

Estratégia: usar AsyncMock para mockar ExemplarRepository, EmprestimoRepository
e InventarioLogRepository — sem dependência de banco de dados, SQLAlchemy ou FastAPI.

Casos cobertos:
  - Happy path: exemplar retornado com estado='baixado' e motivo_baixa correto.
  - ExemplarNotFoundError quando exemplar não existe.
  - ExemplarJaEmprestadoError quando estado == 'emprestado'.
  - ExemplarJaBaixadoError quando estado == 'baixado'.
  - inventario_log_repo.registrar chamado com acao='baixado' no caminho feliz.
  - Nenhuma persistência ocorre quando validações falham.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.entities.exemplar import Exemplar
from app.domain.exceptions import (
    ExemplarJaBaixadoError,
    ExemplarJaEmprestadoError,
    ExemplarNotFoundError,
)
from app.use_cases.baixar_exemplar import BaixarExemplarUseCase

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXEMPLAR_ID = uuid4()
_OPERADOR_ID = "test-token-admin"


def _make_exemplar(estado: str = "disponivel") -> Exemplar:
    return Exemplar(
        id=_EXEMPLAR_ID,
        obra_id=uuid4(),
        codigo_qr="LIB-2025-00001",
        estado=estado,
        localizacao_estante="A-01",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_exemplar_baixado() -> Exemplar:
    return Exemplar(
        id=_EXEMPLAR_ID,
        obra_id=uuid4(),
        codigo_qr="LIB-2025-00001",
        estado="baixado",
        localizacao_estante="A-01",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        motivo_baixa="danificado",
    )


def _build_exemplar_repo(
    *,
    exemplar: Exemplar | None = None,
    exemplar_apos_baixa: Exemplar | None = None,
) -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=exemplar)
    repo.update_baixa = AsyncMock(return_value=exemplar_apos_baixa)
    return repo


def _build_emprestimo_repo() -> MagicMock:
    repo = MagicMock()
    return repo


def _build_log_repo() -> MagicMock:
    repo = MagicMock()
    repo.registrar = AsyncMock(return_value=None)
    return repo


def _build_use_case(
    *,
    exemplar: Exemplar | None = None,
    exemplar_apos_baixa: Exemplar | None = None,
) -> tuple[BaixarExemplarUseCase, MagicMock, MagicMock, MagicMock]:
    exemplar_repo = _build_exemplar_repo(
        exemplar=exemplar,
        exemplar_apos_baixa=exemplar_apos_baixa or _make_exemplar_baixado(),
    )
    emprestimo_repo = _build_emprestimo_repo()
    log_repo = _build_log_repo()
    use_case = BaixarExemplarUseCase(exemplar_repo, emprestimo_repo, log_repo)
    return use_case, exemplar_repo, emprestimo_repo, log_repo


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_baixar_exemplar_retorna_exemplar_com_estado_baixado():
    baixado = _make_exemplar_baixado()
    use_case, _, _, _ = _build_use_case(
        exemplar=_make_exemplar("disponivel"),
        exemplar_apos_baixa=baixado,
    )

    result = await use_case.execute(_EXEMPLAR_ID, "danificado", _OPERADOR_ID)

    assert result.estado == "baixado"


async def test_baixar_exemplar_retorna_motivo_baixa_correto():
    baixado = _make_exemplar_baixado()
    use_case, _, _, _ = _build_use_case(
        exemplar=_make_exemplar("disponivel"),
        exemplar_apos_baixa=baixado,
    )

    result = await use_case.execute(_EXEMPLAR_ID, "danificado", _OPERADOR_ID)

    assert result.motivo_baixa == "danificado"


async def test_baixar_exemplar_chama_update_baixa_com_motivo():
    use_case, exemplar_repo, _, _ = _build_use_case(
        exemplar=_make_exemplar("disponivel"),
    )

    await use_case.execute(_EXEMPLAR_ID, "extraviado", _OPERADOR_ID)

    exemplar_repo.update_baixa.assert_awaited_once_with(_EXEMPLAR_ID, "extraviado")


async def test_baixar_exemplar_registra_log_com_acao_baixado():
    use_case, _, _, log_repo = _build_use_case(
        exemplar=_make_exemplar("disponivel"),
    )

    await use_case.execute(_EXEMPLAR_ID, "danificado", _OPERADOR_ID)

    log_repo.registrar.assert_awaited_once()
    call_kwargs = log_repo.registrar.await_args.kwargs
    assert call_kwargs["acao"] == "baixado"
    assert call_kwargs["exemplar_id"] == _EXEMPLAR_ID
    assert call_kwargs["operador_keycloak_id"] == _OPERADOR_ID


# ---------------------------------------------------------------------------
# ExemplarNotFoundError
# ---------------------------------------------------------------------------


async def test_exemplar_nao_encontrado_levanta_not_found_error():
    use_case, _, _, _ = _build_use_case(exemplar=None)

    with pytest.raises(ExemplarNotFoundError):
        await use_case.execute(_EXEMPLAR_ID, "danificado", _OPERADOR_ID)


async def test_exemplar_nao_encontrado_nao_persiste():
    use_case, exemplar_repo, _, log_repo = _build_use_case(exemplar=None)

    with pytest.raises(ExemplarNotFoundError):
        await use_case.execute(_EXEMPLAR_ID, "danificado", _OPERADOR_ID)

    exemplar_repo.update_baixa.assert_not_called()
    log_repo.registrar.assert_not_called()


# ---------------------------------------------------------------------------
# ExemplarJaEmprestadoError
# ---------------------------------------------------------------------------


async def test_exemplar_emprestado_levanta_ja_emprestado_error():
    use_case, _, _, _ = _build_use_case(exemplar=_make_exemplar("emprestado"))

    with pytest.raises(ExemplarJaEmprestadoError) as exc_info:
        await use_case.execute(_EXEMPLAR_ID, "danificado", _OPERADOR_ID)

    assert exc_info.value.exemplar_id == str(_EXEMPLAR_ID)


async def test_exemplar_emprestado_nao_persiste():
    use_case, exemplar_repo, _, log_repo = _build_use_case(
        exemplar=_make_exemplar("emprestado")
    )

    with pytest.raises(ExemplarJaEmprestadoError):
        await use_case.execute(_EXEMPLAR_ID, "danificado", _OPERADOR_ID)

    exemplar_repo.update_baixa.assert_not_called()
    log_repo.registrar.assert_not_called()


# ---------------------------------------------------------------------------
# ExemplarJaBaixadoError
# ---------------------------------------------------------------------------


async def test_exemplar_ja_baixado_levanta_ja_baixado_error():
    use_case, _, _, _ = _build_use_case(exemplar=_make_exemplar("baixado"))

    with pytest.raises(ExemplarJaBaixadoError) as exc_info:
        await use_case.execute(_EXEMPLAR_ID, "danificado", _OPERADOR_ID)

    assert exc_info.value.exemplar_id == str(_EXEMPLAR_ID)


async def test_exemplar_ja_baixado_nao_persiste():
    use_case, exemplar_repo, _, log_repo = _build_use_case(
        exemplar=_make_exemplar("baixado")
    )

    with pytest.raises(ExemplarJaBaixadoError):
        await use_case.execute(_EXEMPLAR_ID, "danificado", _OPERADOR_ID)

    exemplar_repo.update_baixa.assert_not_called()
    log_repo.registrar.assert_not_called()
