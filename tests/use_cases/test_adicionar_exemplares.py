"""
Testes unitários para AdicionarExemplaresUseCase.

Estratégia: usar unittest.mock.AsyncMock para mockar ObraRepository e
ExemplarRepository, evitando qualquer dependência de banco de dados ou I/O.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.domain.entities.exemplar import Exemplar
from app.domain.entities.obra import Obra
from app.domain.exceptions import ObraNotFoundError
from app.use_cases.adicionar_exemplares import AdicionarExemplaresUseCase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OBRA_ID = uuid4()
_OBRA_ID_INEXISTENTE = UUID("00000000-0000-0000-0000-000000000099")

QR_FORMAT = re.compile(r"^LIB-\d{4}-\d{5}$")


def _make_obra() -> Obra:
    return Obra(
        id=_OBRA_ID,
        isbn="9788535902778",
        titulo="Dom Casmurro",
        autores=["Machado de Assis"],
        editora="Ática",
        ano=1899,
        capa_url=None,
        categoria="Literatura Brasileira",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _build_obra_repo(*, obra: Obra | None) -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=obra)
    return repo


def _build_exemplar_repo(*, existing_count: int = 0) -> MagicMock:
    repo = MagicMock()
    repo.count_all = AsyncMock(return_value=existing_count)
    # save returns the exemplar unchanged (simulates DB persisting it)
    repo.save = AsyncMock(side_effect=lambda e: e)
    return repo


def _make_use_case(
    obra: Obra | None = None,
    existing_count: int = 0,
) -> tuple[AdicionarExemplaresUseCase, MagicMock, MagicMock]:
    obra_repo = _build_obra_repo(obra=obra)
    exemplar_repo = _build_exemplar_repo(existing_count=existing_count)
    use_case = AdicionarExemplaresUseCase(obra_repo, exemplar_repo)
    return use_case, obra_repo, exemplar_repo


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


async def test_cria_quantidade_correta_de_exemplares():
    """execute() deve retornar exatamente N exemplares persistidos."""
    use_case, _, exemplar_repo = _make_use_case(obra=_make_obra())

    result = await use_case.execute(_OBRA_ID, quantidade=3, localizacao_estante="A-01")

    assert len(result) == 3
    assert exemplar_repo.save.await_count == 3


async def test_codigos_qr_tem_formato_correto():
    """Cada código QR deve corresponder ao padrão LIB-{ANO}-{SEQUENCIAL:05d}."""
    use_case, _, _ = _make_use_case(obra=_make_obra())

    result = await use_case.execute(_OBRA_ID, quantidade=2, localizacao_estante="A-01")

    for exemplar in result:
        assert QR_FORMAT.match(exemplar.codigo_qr), (
            f"Formato inválido: {exemplar.codigo_qr}"
        )


async def test_codigos_qr_sao_unicos():
    """Todos os códigos QR gerados na mesma chamada devem ser distintos."""
    use_case, _, _ = _make_use_case(obra=_make_obra())

    result = await use_case.execute(_OBRA_ID, quantidade=5, localizacao_estante="B-03")

    codigos = [e.codigo_qr for e in result]
    assert len(set(codigos)) == len(codigos)


async def test_sequencial_continua_a_partir_do_count_existente():
    """O sequencial do 1º novo exemplar deve ser existing_count + 1."""
    existing_count = 10
    use_case, _, _ = _make_use_case(obra=_make_obra(), existing_count=existing_count)

    result = await use_case.execute(_OBRA_ID, quantidade=3, localizacao_estante="C-02")

    sequenciais = [int(e.codigo_qr.split("-")[2]) for e in result]
    assert sequenciais == [11, 12, 13]


async def test_exemplares_criados_com_estado_disponivel():
    """Todos os exemplares criados devem ter estado 'disponivel'."""
    use_case, _, _ = _make_use_case(obra=_make_obra())

    result = await use_case.execute(_OBRA_ID, quantidade=2, localizacao_estante="D-04")

    for exemplar in result:
        assert exemplar.estado == "disponivel"


async def test_exemplares_herdam_obra_id():
    """Todos os exemplares devem ter obra_id igual ao passado no execute."""
    use_case, _, _ = _make_use_case(obra=_make_obra())

    result = await use_case.execute(_OBRA_ID, quantidade=2, localizacao_estante="E-05")

    for exemplar in result:
        assert exemplar.obra_id == _OBRA_ID


async def test_exemplares_herdam_localizacao_estante():
    """localizacao_estante deve ser propagada para todos os exemplares."""
    use_case, _, _ = _make_use_case(obra=_make_obra())

    result = await use_case.execute(_OBRA_ID, quantidade=2, localizacao_estante="F-06")

    for exemplar in result:
        assert exemplar.localizacao_estante == "F-06"


async def test_obra_inexistente_levanta_obra_not_found_error():
    """Se get_by_id retornar None, deve levantar ObraNotFoundError sem chamar save."""
    use_case, _, exemplar_repo = _make_use_case(obra=None)

    with pytest.raises(ObraNotFoundError):
        await use_case.execute(_OBRA_ID_INEXISTENTE, quantidade=1, localizacao_estante="X-01")

    exemplar_repo.save.assert_not_called()


async def test_obra_inexistente_nao_consulta_count():
    """Quando a obra não existe, count_all não deve ser chamado."""
    use_case, _, exemplar_repo = _make_use_case(obra=None)

    with pytest.raises(ObraNotFoundError):
        await use_case.execute(_OBRA_ID_INEXISTENTE, quantidade=1, localizacao_estante="X-01")

    exemplar_repo.count_all.assert_not_called()
