"""
Testes unitários para EnviarLembretesUseCase.

Estratégia: AsyncMock para todos os repositórios e gateway — sem banco de dados.

Cobre:
  - Happy path: contagem correta de envios.
  - Leitor sem telefone é ignorado silenciosamente (não conta no total).
  - Leitor None é ignorado silenciosamente.
  - Falha no gateway é logada sem interromper o loop (outros envios continuam).
  - Empréstimo com exemplar inexistente usa título vazio.
  - Empréstimo com obra inexistente usa título vazio.
  - Nenhum envio quando não há empréstimos vencendo amanhã.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.domain.entities.emprestimo import Emprestimo
from app.domain.entities.exemplar import Exemplar
from app.domain.entities.leitor import Leitor
from app.domain.entities.obra import Obra
from app.use_cases.enviar_lembretes import EnviarLembretesUseCase

# ---------------------------------------------------------------------------
# Constantes e fábricas
# ---------------------------------------------------------------------------

_LEITOR_ID = uuid4()
_EXEMPLAR_ID = uuid4()
_OBRA_ID = uuid4()
_EMPRESTIMO_ID = uuid4()

_AMANHA = datetime.now(timezone.utc) + timedelta(days=1)


def _make_emprestimo(leitor_id: UUID = _LEITOR_ID) -> Emprestimo:
    return Emprestimo(
        id=_EMPRESTIMO_ID,
        exemplar_id=_EXEMPLAR_ID,
        leitor_id=leitor_id,
        data_checkout=datetime.now(timezone.utc),
        data_prevista=_AMANHA,
        data_devolucao=None,
        renovacoes=0,
        status="ativo",
    )


def _make_leitor(telefone: str | None = "11999990001") -> Leitor:
    return Leitor(
        id=_LEITOR_ID,
        nome="Ana Lima",
        cpf_hash=Leitor.hash_cpf("12345678900"),
        telefone=telefone,
        email="ana@email.com",
        ativo=True,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_exemplar() -> Exemplar:
    return Exemplar(
        id=_EXEMPLAR_ID,
        obra_id=_OBRA_ID,
        codigo_qr="LIB-2025-00001",
        estado="emprestado",
        localizacao_estante="A-01",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_obra() -> Obra:
    return Obra(
        id=_OBRA_ID,
        titulo="Dom Casmurro",
        autores=["Machado de Assis"],
        isbn=None,
        editora="Ática",
        ano=1899,
        categoria="Literatura",
        capa_url=None,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


_UC_SENTINEL = object()


def _build_use_case(
    *,
    emprestimos: list[Emprestimo] | None = None,
    leitor: Leitor | None | object = _UC_SENTINEL,
    exemplar: Exemplar | None | object = _UC_SENTINEL,
    obra: Obra | None | object = _UC_SENTINEL,
    gateway_raises: Exception | None = None,
) -> tuple[EnviarLembretesUseCase, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]:
    if emprestimos is None:
        emprestimos = [_make_emprestimo()]
    if leitor is _UC_SENTINEL:
        leitor = _make_leitor()
    if exemplar is _UC_SENTINEL:
        exemplar = _make_exemplar()
    if obra is _UC_SENTINEL:
        obra = _make_obra()

    emprestimo_repo = MagicMock()
    emprestimo_repo.list_com_vencimento_amanha = AsyncMock(return_value=emprestimos)

    leitor_repo = MagicMock()
    leitor_repo.get_by_id = AsyncMock(return_value=leitor)

    exemplar_repo = MagicMock()
    exemplar_repo.get_by_id = AsyncMock(return_value=exemplar)

    obra_repo = MagicMock()
    obra_repo.get_by_id = AsyncMock(return_value=obra)

    gateway = MagicMock()
    if gateway_raises:
        gateway.enviar = AsyncMock(side_effect=gateway_raises)
    else:
        gateway.enviar = AsyncMock()

    use_case = EnviarLembretesUseCase(
        emprestimo_repo=emprestimo_repo,
        leitor_repo=leitor_repo,
        exemplar_repo=exemplar_repo,
        obra_repo=obra_repo,
        notificacao_gateway=gateway,
    )
    return use_case, emprestimo_repo, leitor_repo, exemplar_repo, obra_repo, gateway


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_retorna_contagem_correta_de_envios():
    """execute() deve retornar o número de notificações enviadas."""
    use_case, *_ = _build_use_case()

    total = await use_case.execute()

    assert total == 1


async def test_chama_gateway_com_dados_corretos():
    """enviar() deve ser chamado com destino=telefone, template correto e params."""
    use_case, _, _, _, _, gateway = _build_use_case()

    await use_case.execute()

    gateway.enviar.assert_awaited_once()
    call_kwargs = gateway.enviar.call_args.kwargs
    assert call_kwargs["destino"] == "11999990001"
    assert call_kwargs["template"] == "lembrete_devolucao"
    assert "nome" in call_kwargs["params"]
    assert "titulo" in call_kwargs["params"]
    assert "data_prevista" in call_kwargs["params"]


async def test_params_contem_titulo_da_obra():
    """params deve conter o título da obra."""
    use_case, *_, gateway = _build_use_case()

    await use_case.execute()

    params = gateway.enviar.call_args.kwargs["params"]
    assert params["titulo"] == "Dom Casmurro"


async def test_multiplos_emprestimos_retorna_total_correto():
    """Com 3 empréstimos de leitores distintos, retorna total=3."""
    leitor_a = _make_leitor(telefone="11999990001")
    leitor_b = _make_leitor(telefone="11999990002")
    leitor_c = _make_leitor(telefone="11999990003")
    id_a, id_b, id_c = uuid4(), uuid4(), uuid4()

    emp_a = _make_emprestimo(leitor_id=id_a)
    emp_b = _make_emprestimo(leitor_id=id_b)
    emp_c = _make_emprestimo(leitor_id=id_c)

    emprestimo_repo = MagicMock()
    emprestimo_repo.list_com_vencimento_amanha = AsyncMock(return_value=[emp_a, emp_b, emp_c])
    leitor_repo = MagicMock()
    leitor_repo.get_by_id = AsyncMock(side_effect=[leitor_a, leitor_b, leitor_c])
    exemplar_repo = MagicMock()
    exemplar_repo.get_by_id = AsyncMock(return_value=_make_exemplar())
    obra_repo = MagicMock()
    obra_repo.get_by_id = AsyncMock(return_value=_make_obra())
    gateway = MagicMock()
    gateway.enviar = AsyncMock()

    use_case = EnviarLembretesUseCase(
        emprestimo_repo=emprestimo_repo,
        leitor_repo=leitor_repo,
        exemplar_repo=exemplar_repo,
        obra_repo=obra_repo,
        notificacao_gateway=gateway,
    )

    total = await use_case.execute()

    assert total == 3
    assert gateway.enviar.await_count == 3


# ---------------------------------------------------------------------------
# Leitor sem telefone
# ---------------------------------------------------------------------------


async def test_leitor_sem_telefone_ignorado_silenciosamente():
    """Leitor com telefone=None não deve resultar em chamada ao gateway."""
    use_case, _, _, _, _, gateway = _build_use_case(leitor=_make_leitor(telefone=None))

    total = await use_case.execute()

    assert total == 0
    gateway.enviar.assert_not_called()


async def test_leitor_com_telefone_vazio_ignorado():
    """Leitor com telefone='' não deve resultar em chamada ao gateway."""
    use_case, _, _, _, _, gateway = _build_use_case(leitor=_make_leitor(telefone=""))

    total = await use_case.execute()

    assert total == 0
    gateway.enviar.assert_not_called()


async def test_leitor_none_ignorado_silenciosamente():
    """Leitor inexistente (None) não deve resultar em chamada ao gateway."""
    use_case, _, _, _, _, gateway = _build_use_case(leitor=None)

    total = await use_case.execute()

    assert total == 0
    gateway.enviar.assert_not_called()


# ---------------------------------------------------------------------------
# Falha no gateway
# ---------------------------------------------------------------------------


async def test_falha_no_gateway_nao_interrompe_loop():
    """Exceção no gateway deve ser capturada; os demais empréstimos continuam."""
    leitor_a = _make_leitor(telefone="11999990001")
    leitor_b = _make_leitor(telefone="11999990002")
    id_a, id_b = uuid4(), uuid4()
    emp_a = _make_emprestimo(leitor_id=id_a)
    emp_b = _make_emprestimo(leitor_id=id_b)

    emprestimo_repo = MagicMock()
    emprestimo_repo.list_com_vencimento_amanha = AsyncMock(return_value=[emp_a, emp_b])
    leitor_repo = MagicMock()
    leitor_repo.get_by_id = AsyncMock(side_effect=[leitor_a, leitor_b])
    exemplar_repo = MagicMock()
    exemplar_repo.get_by_id = AsyncMock(return_value=_make_exemplar())
    obra_repo = MagicMock()
    obra_repo.get_by_id = AsyncMock(return_value=_make_obra())
    gateway = MagicMock()
    # Primeiro envio falha, segundo sucede
    gateway.enviar = AsyncMock(side_effect=[RuntimeError("API down"), None])

    use_case = EnviarLembretesUseCase(
        emprestimo_repo=emprestimo_repo,
        leitor_repo=leitor_repo,
        exemplar_repo=exemplar_repo,
        obra_repo=obra_repo,
        notificacao_gateway=gateway,
    )

    total = await use_case.execute()

    # Segundo envio deve ocorrer mesmo com o primeiro falhando
    assert gateway.enviar.await_count == 2
    assert total == 1  # Apenas o segundo contou


# ---------------------------------------------------------------------------
# Sem empréstimos
# ---------------------------------------------------------------------------


async def test_sem_emprestimos_retorna_zero():
    """Sem empréstimos vencendo amanhã, deve retornar 0."""
    use_case, _, _, _, _, gateway = _build_use_case(emprestimos=[])

    total = await use_case.execute()

    assert total == 0
    gateway.enviar.assert_not_called()


# ---------------------------------------------------------------------------
# Exemplar/Obra não encontrados
# ---------------------------------------------------------------------------


async def test_exemplar_nao_encontrado_usa_titulo_vazio():
    """Quando exemplar não existe, título deve ser vazio mas envio ocorre."""
    use_case, _, _, exemplar_repo, _, gateway = _build_use_case(exemplar=None)
    exemplar_repo.get_by_id = AsyncMock(return_value=None)

    total = await use_case.execute()

    assert total == 1
    params = gateway.enviar.call_args.kwargs["params"]
    assert params["titulo"] == ""


async def test_obra_nao_encontrada_usa_titulo_vazio():
    """Quando obra não existe, título deve ser vazio mas envio ocorre."""
    use_case, _, _, _, obra_repo, gateway = _build_use_case(obra=None)
    obra_repo.get_by_id = AsyncMock(return_value=None)

    total = await use_case.execute()

    assert total == 1
    params = gateway.enviar.call_args.kwargs["params"]
    assert params["titulo"] == ""
