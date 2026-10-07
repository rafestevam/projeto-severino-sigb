"""
Testes unitários para RealizarInventarioUseCase (US-019).

Estratégia: usar AsyncMock para mockar ExemplarRepository e
InventarioLogRepository — sem dependência de banco de dados, SQLAlchemy ou FastAPI.

Casos cobertos:
  - Happy path: resultado correto para encontrados, nao_bipados, nao_esperados.
  - Exemplar emprestado não aparece em nao_bipados (list_by_localizacao filtra por 'disponivel').
  - Exemplar de outra estante aparece em nao_esperados.
  - QR Code desconhecido (não encontrado no banco) é ignorado silenciosamente.
  - inventario_log_repo.registrar chamado para cada QR encontrado.
  - inventario_log_repo.registrar não chamado para QRs em nao_esperados.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

import pytest

from app.domain.entities.exemplar import Exemplar
from app.use_cases.realizar_inventario import (
    ExemplarResumo,
    InventarioResultado,
    RealizarInventarioUseCase,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OPERADOR_ID = "test-token-admin"


def _make_exemplar(
    codigo_qr: str,
    estado: str = "disponivel",
    localizacao: str = "A-01",
) -> Exemplar:
    return Exemplar(
        id=uuid4(),
        obra_id=uuid4(),
        codigo_qr=codigo_qr,
        estado=estado,
        localizacao_estante=localizacao,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _build_exemplar_repo(
    *,
    by_qr: dict[str, Exemplar | None] | None = None,
    por_localizacao: list[Exemplar] | None = None,
) -> MagicMock:
    repo = MagicMock()
    by_qr = by_qr or {}
    por_localizacao = por_localizacao or []

    async def _get_by_qr(codigo_qr: str) -> Exemplar | None:
        return by_qr.get(codigo_qr)

    repo.get_by_codigo_qr = AsyncMock(side_effect=_get_by_qr)
    repo.list_by_localizacao = AsyncMock(return_value=por_localizacao)
    return repo


def _build_log_repo() -> MagicMock:
    repo = MagicMock()
    repo.registrar = AsyncMock(return_value=None)
    return repo


def _build_use_case(
    *,
    by_qr: dict[str, Exemplar | None] | None = None,
    por_localizacao: list[Exemplar] | None = None,
) -> tuple[RealizarInventarioUseCase, MagicMock, MagicMock]:
    exemplar_repo = _build_exemplar_repo(by_qr=by_qr, por_localizacao=por_localizacao)
    log_repo = _build_log_repo()
    use_case = RealizarInventarioUseCase(exemplar_repo, log_repo)
    return use_case, exemplar_repo, log_repo


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_inventario_retorna_encontrado_quando_qr_e_localizacao_batem():
    ex = _make_exemplar("QR-001", localizacao="A-01")
    use_case, _, _ = _build_use_case(
        by_qr={"QR-001": ex},
        por_localizacao=[ex],
    )

    resultado = await use_case.execute(["QR-001"], "A-01", _OPERADOR_ID)

    assert len(resultado.encontrados) == 1
    assert resultado.encontrados[0].codigo_qr == "QR-001"
    assert resultado.nao_bipados == []
    assert resultado.nao_esperados == []


async def test_inventario_retorna_nao_bipado_quando_exemplar_disponivel_nao_bipado():
    ex_presente = _make_exemplar("QR-001", localizacao="A-01")
    ex_ausente = _make_exemplar("QR-002", localizacao="A-01")
    use_case, _, _ = _build_use_case(
        by_qr={"QR-001": ex_presente},
        por_localizacao=[ex_presente, ex_ausente],
    )

    resultado = await use_case.execute(["QR-001"], "A-01", _OPERADOR_ID)

    nao_bipados_qrs = [e.codigo_qr for e in resultado.nao_bipados]
    assert "QR-002" in nao_bipados_qrs
    assert "QR-001" not in nao_bipados_qrs


async def test_inventario_retorna_nao_esperado_quando_localizacao_diferente():
    ex_outra_estante = _make_exemplar("QR-003", localizacao="B-02")
    use_case, _, _ = _build_use_case(
        by_qr={"QR-003": ex_outra_estante},
        por_localizacao=[],  # nenhum disponível na estante A-01
    )

    resultado = await use_case.execute(["QR-003"], "A-01", _OPERADOR_ID)

    assert len(resultado.nao_esperados) == 1
    assert resultado.nao_esperados[0].codigo_qr == "QR-003"
    assert resultado.encontrados == []
    assert resultado.nao_bipados == []


async def test_inventario_qr_desconhecido_ignorado_silenciosamente():
    use_case, _, _ = _build_use_case(
        by_qr={"QR-INVALIDO": None},
        por_localizacao=[],
    )

    resultado = await use_case.execute(["QR-INVALIDO"], "A-01", _OPERADOR_ID)

    assert resultado.encontrados == []
    assert resultado.nao_bipados == []
    assert resultado.nao_esperados == []


async def test_inventario_resultado_tipo_correto():
    use_case, _, _ = _build_use_case()

    resultado = await use_case.execute([], "A-01", _OPERADOR_ID)

    assert isinstance(resultado, InventarioResultado)
    assert isinstance(resultado.encontrados, list)
    assert isinstance(resultado.nao_bipados, list)
    assert isinstance(resultado.nao_esperados, list)


# ---------------------------------------------------------------------------
# Exemplar emprestado não entra em nao_bipados
# ---------------------------------------------------------------------------


async def test_exemplar_emprestado_nao_aparece_em_nao_bipados():
    """list_by_localizacao filtra por 'disponivel', portanto emprestados não retornam."""
    # O repositório só retorna disponíveis — o emprestado não aparece na lista
    use_case, exemplar_repo, _ = _build_use_case(
        by_qr={},
        por_localizacao=[],  # emprestado não está em disponíveis da estante
    )

    resultado = await use_case.execute([], "A-01", _OPERADOR_ID)

    assert resultado.nao_bipados == []


# ---------------------------------------------------------------------------
# Log registrado apenas para encontrados
# ---------------------------------------------------------------------------


async def test_log_registrado_para_cada_qr_encontrado():
    ex1 = _make_exemplar("QR-001", localizacao="A-01")
    ex2 = _make_exemplar("QR-002", localizacao="A-01")
    use_case, _, log_repo = _build_use_case(
        by_qr={"QR-001": ex1, "QR-002": ex2},
        por_localizacao=[ex1, ex2],
    )

    await use_case.execute(["QR-001", "QR-002"], "A-01", _OPERADOR_ID)

    assert log_repo.registrar.await_count == 2
    acoes = [c.kwargs["acao"] for c in log_repo.registrar.await_args_list]
    assert all(a == "encontrado" for a in acoes)


async def test_log_nao_registrado_para_qr_nao_esperado():
    ex_outra_estante = _make_exemplar("QR-999", localizacao="Z-99")
    use_case, _, log_repo = _build_use_case(
        by_qr={"QR-999": ex_outra_estante},
        por_localizacao=[],
    )

    await use_case.execute(["QR-999"], "A-01", _OPERADOR_ID)

    log_repo.registrar.assert_not_awaited()


async def test_log_nao_registrado_para_qr_desconhecido():
    use_case, _, log_repo = _build_use_case(
        by_qr={"QR-X": None},
        por_localizacao=[],
    )

    await use_case.execute(["QR-X"], "A-01", _OPERADOR_ID)

    log_repo.registrar.assert_not_awaited()


async def test_log_registrado_com_operador_correto():
    ex = _make_exemplar("QR-001", localizacao="A-01")
    use_case, _, log_repo = _build_use_case(
        by_qr={"QR-001": ex},
        por_localizacao=[ex],
    )

    await use_case.execute(["QR-001"], "A-01", "operador-xyz")

    call_kwargs = log_repo.registrar.await_args_list[0].kwargs
    assert call_kwargs["operador_keycloak_id"] == "operador-xyz"
    assert call_kwargs["exemplar_id"] == ex.id
