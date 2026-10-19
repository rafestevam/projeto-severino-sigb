"""
Testes unitários para ObterObraPublicaUseCase (US-029).

Estratégia: AsyncMock para os repositórios — sem banco de dados.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.entities.disponibilidade_obra import DisponibilidadeObra
from app.domain.exceptions import ObraNotFoundError
from app.use_cases.obter_obra_publica import ObterObraPublicaUseCase
from tests.domain.repositories.conftest import make_obra


def _build(obra, disponibilidades, posicao=None):
    obra_repo = MagicMock()
    obra_repo.get_by_id = AsyncMock(return_value=obra)
    obra_repo.get_posicao_ranking = AsyncMock(return_value=posicao)
    exemplar_repo = MagicMock()
    exemplar_repo.contar_disponibilidade = AsyncMock(return_value=disponibilidades)
    return ObterObraPublicaUseCase(obra_repo, exemplar_repo), obra_repo


async def test_retorna_obra_disponibilidade_e_ranking() -> None:
    obra = make_obra(id=uuid4())
    disp = DisponibilidadeObra(obra.id, disponiveis=2, emprestados=1)
    use_case, _ = _build(obra, {obra.id: disp}, posicao=3)

    detalhe = await use_case.execute(obra.id)

    assert detalhe.obra == obra
    assert detalhe.disponibilidade == disp
    assert detalhe.posicao_ranking == 3


async def test_ranking_none_quando_obra_nunca_emprestada() -> None:
    obra = make_obra(id=uuid4())
    use_case, _ = _build(obra, {obra.id: DisponibilidadeObra(obra.id, 1, 0)}, posicao=None)

    detalhe = await use_case.execute(obra.id)

    assert detalhe.posicao_ranking is None


async def test_lanca_not_found_para_obra_inexistente() -> None:
    use_case, _ = _build(None, {})

    with pytest.raises(ObraNotFoundError):
        await use_case.execute(uuid4())


async def test_lanca_not_found_para_obra_sem_exemplares_ativos() -> None:
    """D3: obra só com exemplares baixados não pode ter sua existência revelada."""
    obra = make_obra(id=uuid4())
    use_case, obra_repo = _build(obra, {})

    with pytest.raises(ObraNotFoundError):
        await use_case.execute(obra.id)
    obra_repo.get_posicao_ranking.assert_not_awaited()
