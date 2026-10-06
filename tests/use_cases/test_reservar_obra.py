"""
Testes unitários para ReservarObraUseCase e CancelarReservaUseCase.

Estratégia: AsyncMock para todos os repositórios — sem banco de dados.

ReservarObraUseCase cobre:
  - Happy path: reserva criada, posição 1 na fila.
  - Posição correta quando já existe reserva aguardando.
  - LeitorInativoError: leitor None.
  - LeitorInativoError: leitor inativo (ativo=False).
  - ObraComExemplarDisponivelError: há exemplar disponível.
  - ReservaJaExisteError: leitor já tem reserva ativa para a mesma obra.
  - Não persiste quando validações falham.

CancelarReservaUseCase cobre:
  - Happy path: status atualizado para 'expirada'.
  - ReservaNaoEncontradaError: reserva inexistente.
  - Não chama update_status quando reserva não existe.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.domain.entities.exemplar import Exemplar
from app.domain.entities.leitor import Leitor
from app.domain.entities.reserva import Reserva
from app.domain.exceptions import (
    LeitorInativoError,
    ObraComExemplarDisponivelError,
    ReservaJaExisteError,
    ReservaNaoEncontradaError,
)
from app.use_cases.cancelar_reserva import CancelarReservaUseCase
from app.use_cases.reservar_obra import ReservarObraUseCase

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_OBRA_ID = uuid4()
_LEITOR_ID = uuid4()
_RESERVA_ID = uuid4()


# ---------------------------------------------------------------------------
# Fábricas de entidades
# ---------------------------------------------------------------------------


def _make_leitor(ativo: bool = True) -> Leitor:
    return Leitor(
        id=_LEITOR_ID,
        nome="Ana Lima",
        cpf_hash=Leitor.hash_cpf("12345678900"),
        telefone="11999990001",
        email="ana@email.com",
        ativo=ativo,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_exemplar(estado: str = "emprestado") -> Exemplar:
    return Exemplar(
        id=uuid4(),
        obra_id=_OBRA_ID,
        codigo_qr="LIB-2025-00001",
        estado=estado,
        localizacao_estante="A-01",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_reserva(
    status: str = "aguardando",
    leitor_id: UUID = _LEITOR_ID,
    obra_id: UUID = _OBRA_ID,
) -> Reserva:
    return Reserva(
        id=_RESERVA_ID,
        obra_id=obra_id,
        leitor_id=leitor_id,
        status=status,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Fábricas de mocks
# ---------------------------------------------------------------------------


def _build_leitor_repo(*, leitor: Leitor | None) -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=leitor)
    return repo


def _build_exemplar_repo(*, exemplares: list[Exemplar] | None = None) -> MagicMock:
    if exemplares is None:
        exemplares = [_make_exemplar("emprestado")]
    repo = MagicMock()
    repo.list_by_obra = AsyncMock(return_value=exemplares)
    return repo


def _build_reserva_repo(
    *,
    reserva_existente: Reserva | None = None,
    reservas_na_fila: list[Reserva] | None = None,
    reserva_salva: Reserva | None = None,
    reserva_para_get: Reserva | None = None,
    reserva_apos_update: Reserva | None = None,
) -> MagicMock:
    repo = MagicMock()
    repo.get_ativa_by_leitor_e_obra = AsyncMock(return_value=reserva_existente)
    if reserva_salva is None:
        reserva_salva = _make_reserva()
    repo.save = AsyncMock(return_value=reserva_salva)
    if reservas_na_fila is None:
        reservas_na_fila = [reserva_salva]
    repo.list_by_obra = AsyncMock(return_value=reservas_na_fila)
    repo.get_by_id = AsyncMock(return_value=reserva_para_get)
    if reserva_apos_update is None:
        reserva_apos_update = _make_reserva(status="expirada")
    repo.update_status = AsyncMock(return_value=reserva_apos_update)
    return repo


_SENTINEL = object()


def _build_reservar_use_case(
    *,
    leitor: Leitor | None | object = _SENTINEL,
    exemplares: list[Exemplar] | None = None,
    reserva_existente: Reserva | None = None,
    reservas_na_fila: list[Reserva] | None = None,
):
    if leitor is _SENTINEL:
        leitor = _make_leitor()
    leitor_repo = _build_leitor_repo(leitor=leitor)  # type: ignore[arg-type]
    exemplar_repo = _build_exemplar_repo(exemplares=exemplares)
    reserva_salva = _make_reserva()
    reserva_repo = _build_reserva_repo(
        reserva_existente=reserva_existente,
        reservas_na_fila=reservas_na_fila,
        reserva_salva=reserva_salva,
    )
    use_case = ReservarObraUseCase(
        exemplar_repo=exemplar_repo,
        leitor_repo=leitor_repo,
        reserva_repo=reserva_repo,
    )
    return use_case, leitor_repo, exemplar_repo, reserva_repo


# ===========================================================================
# ReservarObraUseCase — Happy path
# ===========================================================================


async def test_reservar_obra_retorna_reserva_e_posicao():
    """execute() retorna tupla (Reserva, int) no caminho feliz."""
    use_case, *_ = _build_reservar_use_case()

    reserva, posicao = await use_case.execute(_OBRA_ID, _LEITOR_ID)

    assert isinstance(reserva, Reserva)
    assert isinstance(posicao, int)
    assert posicao >= 1


async def test_reservar_obra_status_aguardando():
    """A reserva criada deve ter status='aguardando'."""
    use_case, *_ = _build_reservar_use_case()

    reserva, _ = await use_case.execute(_OBRA_ID, _LEITOR_ID)

    assert reserva.status == "aguardando"


async def test_reservar_obra_posicao_1_quando_fila_vazia():
    """Posição na fila deve ser 1 quando não há outras reservas aguardando."""
    reserva_salva = _make_reserva(status="aguardando")
    use_case, _, _, reserva_repo = _build_reservar_use_case()
    # Fila contém apenas a reserva recém-criada
    reserva_repo.list_by_obra = AsyncMock(return_value=[reserva_salva])

    _, posicao = await use_case.execute(_OBRA_ID, _LEITOR_ID)

    assert posicao == 1


async def test_reservar_obra_posicao_2_quando_uma_na_fila():
    """Posição na fila deve ser 2 quando já existe 1 reserva aguardando."""
    reserva_existente_na_fila = _make_reserva(status="aguardando", leitor_id=uuid4())
    nova_reserva = _make_reserva(status="aguardando")
    leitor_repo = _build_leitor_repo(leitor=_make_leitor())
    exemplar_repo = _build_exemplar_repo()
    reserva_repo = _build_reserva_repo(
        reservas_na_fila=[reserva_existente_na_fila, nova_reserva],
        reserva_salva=nova_reserva,
    )
    use_case = ReservarObraUseCase(exemplar_repo, leitor_repo, reserva_repo)

    _, posicao = await use_case.execute(_OBRA_ID, _LEITOR_ID)

    assert posicao == 2


async def test_reservar_obra_chama_save():
    """reserva_repo.save deve ser chamado com a nova reserva."""
    use_case, _, _, reserva_repo = _build_reservar_use_case()

    await use_case.execute(_OBRA_ID, _LEITOR_ID)

    reserva_repo.save.assert_awaited_once()


async def test_reservar_obra_ids_corretos():
    """A reserva salva deve ter obra_id e leitor_id corretos."""
    use_case, _, _, reserva_repo = _build_reservar_use_case()
    reserva_repo.save = AsyncMock(side_effect=lambda r: r)
    reserva_repo.list_by_obra = AsyncMock(return_value=[_make_reserva()])

    reserva, _ = await use_case.execute(_OBRA_ID, _LEITOR_ID)

    assert reserva.obra_id == _OBRA_ID
    assert reserva.leitor_id == _LEITOR_ID


# ===========================================================================
# ReservarObraUseCase — LeitorInativoError
# ===========================================================================


async def test_reservar_leitor_none_levanta_leitor_inativo_error():
    """Leitor inexistente (None) deve levantar LeitorInativoError."""
    use_case, *_ = _build_reservar_use_case(leitor=None)

    with pytest.raises(LeitorInativoError) as exc_info:
        await use_case.execute(_OBRA_ID, _LEITOR_ID)

    assert exc_info.value.leitor_id == str(_LEITOR_ID)


async def test_reservar_leitor_inativo_levanta_leitor_inativo_error():
    """Leitor com ativo=False deve levantar LeitorInativoError."""
    use_case, *_ = _build_reservar_use_case(leitor=_make_leitor(ativo=False))

    with pytest.raises(LeitorInativoError):
        await use_case.execute(_OBRA_ID, _LEITOR_ID)


async def test_reservar_leitor_inativo_nao_persiste():
    """Quando leitor inativo, save não deve ser chamado."""
    use_case, _, _, reserva_repo = _build_reservar_use_case(leitor=None)

    with pytest.raises(LeitorInativoError):
        await use_case.execute(_OBRA_ID, _LEITOR_ID)

    reserva_repo.save.assert_not_called()


# ===========================================================================
# ReservarObraUseCase — ObraComExemplarDisponivelError
# ===========================================================================


async def test_reservar_com_exemplar_disponivel_levanta_erro():
    """Obra com exemplar 'disponivel' deve levantar ObraComExemplarDisponivelError."""
    use_case, *_ = _build_reservar_use_case(
        exemplares=[_make_exemplar("disponivel")]
    )

    with pytest.raises(ObraComExemplarDisponivelError) as exc_info:
        await use_case.execute(_OBRA_ID, _LEITOR_ID)

    assert exc_info.value.obra_id == str(_OBRA_ID)


async def test_reservar_com_exemplar_disponivel_nao_persiste():
    """Quando há exemplar disponível, save não deve ser chamado."""
    use_case, _, _, reserva_repo = _build_reservar_use_case(
        exemplares=[_make_exemplar("disponivel")]
    )

    with pytest.raises(ObraComExemplarDisponivelError):
        await use_case.execute(_OBRA_ID, _LEITOR_ID)

    reserva_repo.save.assert_not_called()


async def test_reservar_exemplar_emprestado_permite_reserva():
    """Todos os exemplares emprestados: reserva deve ser criada."""
    use_case, *_ = _build_reservar_use_case(
        exemplares=[_make_exemplar("emprestado"), _make_exemplar("emprestado")]
    )

    reserva, posicao = await use_case.execute(_OBRA_ID, _LEITOR_ID)

    assert isinstance(reserva, Reserva)


# ===========================================================================
# ReservarObraUseCase — ReservaJaExisteError
# ===========================================================================


async def test_reservar_com_reserva_ja_existente_levanta_erro():
    """Leitor com reserva ativa para a mesma obra deve levantar ReservaJaExisteError."""
    reserva_ativa = _make_reserva(status="aguardando")
    use_case, *_ = _build_reservar_use_case(reserva_existente=reserva_ativa)

    with pytest.raises(ReservaJaExisteError) as exc_info:
        await use_case.execute(_OBRA_ID, _LEITOR_ID)

    assert exc_info.value.obra_id == str(_OBRA_ID)
    assert exc_info.value.leitor_id == str(_LEITOR_ID)


async def test_reservar_com_reserva_ja_existente_nao_persiste():
    """Quando reserva já existe, save não deve ser chamado."""
    reserva_ativa = _make_reserva(status="disponivel")
    use_case, _, _, reserva_repo = _build_reservar_use_case(reserva_existente=reserva_ativa)

    with pytest.raises(ReservaJaExisteError):
        await use_case.execute(_OBRA_ID, _LEITOR_ID)

    reserva_repo.save.assert_not_called()


# ===========================================================================
# CancelarReservaUseCase — Happy path
# ===========================================================================


async def test_cancelar_reserva_retorna_reserva_expirada():
    """execute() deve retornar reserva com status 'expirada'."""
    reserva_para_get = _make_reserva(status="aguardando")
    reserva_atualizada = _make_reserva(status="expirada")
    reserva_repo = _build_reserva_repo(
        reserva_para_get=reserva_para_get,
        reserva_apos_update=reserva_atualizada,
    )
    use_case = CancelarReservaUseCase(reserva_repo=reserva_repo)

    result = await use_case.execute(_RESERVA_ID)

    assert result.status == "expirada"


async def test_cancelar_reserva_chama_update_status_com_expirada():
    """update_status deve ser chamado com id correto e status 'expirada'."""
    reserva_para_get = _make_reserva(status="aguardando")
    reserva_repo = _build_reserva_repo(reserva_para_get=reserva_para_get)
    use_case = CancelarReservaUseCase(reserva_repo=reserva_repo)

    await use_case.execute(_RESERVA_ID)

    reserva_repo.update_status.assert_awaited_once_with(_RESERVA_ID, "expirada")


# ===========================================================================
# CancelarReservaUseCase — ReservaNaoEncontradaError
# ===========================================================================


async def test_cancelar_reserva_inexistente_levanta_nao_encontrada_error():
    """Reserva inexistente deve levantar ReservaNaoEncontradaError."""
    reserva_repo = _build_reserva_repo(reserva_para_get=None)
    use_case = CancelarReservaUseCase(reserva_repo=reserva_repo)

    with pytest.raises(ReservaNaoEncontradaError) as exc_info:
        await use_case.execute(_RESERVA_ID)

    assert exc_info.value.identifier == str(_RESERVA_ID)


async def test_cancelar_reserva_inexistente_nao_chama_update_status():
    """Quando reserva não existe, update_status não deve ser chamado."""
    reserva_repo = _build_reserva_repo(reserva_para_get=None)
    use_case = CancelarReservaUseCase(reserva_repo=reserva_repo)

    with pytest.raises(ReservaNaoEncontradaError):
        await use_case.execute(_RESERVA_ID)

    reserva_repo.update_status.assert_not_called()
