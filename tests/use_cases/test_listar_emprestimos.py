"""
Testes unitários para ListarEmprestimosUseCase.

Estratégia: usar unittest.mock.AsyncMock para mockar EmprestimoRepository,
ExemplarRepository e ObraRepository — sem dependência de banco de dados,
SQLAlchemy ou FastAPI.

Casos cobertos:
  - Delegação ao repositório com todos os parâmetros recebidos.
  - Valores padrão (page=1, page_size=20, leitor_id=None, status=None).
  - Retorno de lista vazia com total 0.
  - Enriquecimento com titulo_obra via exemplar + obra.
  - titulo_obra = 'Obra desconhecida' quando exemplar não encontrado.
  - titulo_obra = 'Obra desconhecida' quando obra não encontrada.
  - Múltiplos itens: cada empréstimo recebe o título correto.
  - Filtro por leitor_id é repassado ao repositório.
  - Filtro por status é repassado ao repositório.
  - Filtros combinados são repassados ao repositório.
  - Paginação (page, page_size) é repassada ao repositório.
  - EmprestimoComTitulo preserva todos os campos de Emprestimo.
  - Total devolvido é o total vindo do repositório (não len da lista).
  - exemplar_repo.get_by_id chamado com exemplar_id correto.
  - obra_repo.get_by_id chamado com obra_id correto do exemplar.
  - Empréstimos sem exemplar e sem obra não levantam exceção.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, call
from uuid import UUID, uuid4

import pytest

from app.domain.entities.emprestimo import Emprestimo, EmprestimoComTitulo
from app.domain.entities.exemplar import Exemplar
from app.domain.entities.obra import Obra
from app.use_cases.listar_emprestimos import ListarEmprestimosUseCase


# ---------------------------------------------------------------------------
# Constantes e helpers
# ---------------------------------------------------------------------------

_LEITOR_ID = uuid4()
_OBRA_ID = uuid4()
_EXEMPLAR_ID = uuid4()

_TITULO = "Dom Casmurro"
_TITULO_DESCONHECIDO = "Obra desconhecida"


def _make_emprestimo(
    *,
    id: UUID | None = None,
    exemplar_id: UUID = _EXEMPLAR_ID,
    leitor_id: UUID = _LEITOR_ID,
    status: str = "ativo",
    renovacoes: int = 0,
    data_devolucao: datetime | None = None,
) -> Emprestimo:
    now = datetime.now(timezone.utc)
    return Emprestimo(
        id=id or uuid4(),
        exemplar_id=exemplar_id,
        leitor_id=leitor_id,
        data_checkout=now - timedelta(days=5),
        data_prevista=now + timedelta(days=9),
        data_devolucao=data_devolucao,
        renovacoes=renovacoes,
        status=status,  # type: ignore[arg-type]
    )


def _make_exemplar(
    *,
    id: UUID = _EXEMPLAR_ID,
    obra_id: UUID = _OBRA_ID,
) -> Exemplar:
    return Exemplar(
        id=id,
        obra_id=obra_id,
        codigo_qr="LIB-2025-00001",
        estado="disponivel",
        localizacao_estante="A-01",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_obra(*, id: UUID = _OBRA_ID, titulo: str = _TITULO) -> Obra:
    return Obra(
        id=id,
        isbn="9788535902778",
        titulo=titulo,
        autores=["Machado de Assis"],
        editora="Ática",
        ano=1899,
        capa_url="",
        categoria="Literatura Brasileira",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _build_emprestimo_repo(
    emprestimos: list[Emprestimo],
    total: int | None = None,
) -> MagicMock:
    repo = MagicMock()
    repo.list_filtered = AsyncMock(
        return_value=(emprestimos, total if total is not None else len(emprestimos))
    )
    return repo


def _build_exemplar_repo(exemplar: Exemplar | None = None) -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=exemplar)
    return repo


def _build_obra_repo(obra: Obra | None = None) -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=obra)
    return repo


def _build_use_case(
    emprestimos: list[Emprestimo],
    *,
    total: int | None = None,
    exemplar: Exemplar | None = None,
    obra: Obra | None = None,
) -> tuple[ListarEmprestimosUseCase, MagicMock, MagicMock, MagicMock]:
    emp_repo = _build_emprestimo_repo(emprestimos, total)
    ex_repo = _build_exemplar_repo(exemplar)
    ob_repo = _build_obra_repo(obra)
    use_case = ListarEmprestimosUseCase(emp_repo, ex_repo, ob_repo)
    return use_case, emp_repo, ex_repo, ob_repo


# ---------------------------------------------------------------------------
# Testes de delegação ao repositório
# ---------------------------------------------------------------------------


async def test_execute_delega_todos_parametros_para_list_filtered():
    """Todos os parâmetros recebidos são repassados ao EmprestimoRepository."""
    leitor_id = uuid4()
    use_case, emp_repo, *_ = _build_use_case([])

    await use_case.execute(leitor_id=leitor_id, status="ativo", page=3, page_size=10)

    emp_repo.list_filtered.assert_awaited_once_with(
        leitor_id=leitor_id,
        status="ativo",
        page=3,
        page_size=10,
    )


async def test_execute_usa_valores_padrao():
    """Sem argumentos, execute() usa leitor_id=None, status=None, page=1, page_size=20."""
    use_case, emp_repo, *_ = _build_use_case([])

    await use_case.execute()

    emp_repo.list_filtered.assert_awaited_once_with(
        leitor_id=None,
        status=None,
        page=1,
        page_size=20,
    )


async def test_execute_filtra_por_leitor_id():
    """Filtro por leitor_id é repassado ao repositório; demais ficam como default."""
    leitor_id = uuid4()
    use_case, emp_repo, *_ = _build_use_case([])

    await use_case.execute(leitor_id=leitor_id)

    emp_repo.list_filtered.assert_awaited_once_with(
        leitor_id=leitor_id,
        status=None,
        page=1,
        page_size=20,
    )


async def test_execute_filtra_por_status():
    """Filtro por status é repassado ao repositório; demais ficam como default."""
    use_case, emp_repo, *_ = _build_use_case([])

    await use_case.execute(status="atrasado")

    emp_repo.list_filtered.assert_awaited_once_with(
        leitor_id=None,
        status="atrasado",
        page=1,
        page_size=20,
    )


async def test_execute_repassa_paginacao():
    """page e page_size são repassados ao repositório."""
    use_case, emp_repo, *_ = _build_use_case([])

    await use_case.execute(page=5, page_size=50)

    emp_repo.list_filtered.assert_awaited_once_with(
        leitor_id=None,
        status=None,
        page=5,
        page_size=50,
    )


# ---------------------------------------------------------------------------
# Testes de retorno
# ---------------------------------------------------------------------------


async def test_execute_retorna_lista_vazia_e_total_zero():
    """Lista vazia com total 0 é devolvida sem erro."""
    use_case, *_ = _build_use_case([], total=0)

    result, total = await use_case.execute()

    assert result == []
    assert total == 0


async def test_execute_retorna_total_do_repositorio_nao_len_da_lista():
    """O total devolvido é o total vindo do repositório, não len(lista)."""
    emp = _make_emprestimo()
    exemplar = _make_exemplar(id=emp.exemplar_id)
    obra = _make_obra()
    use_case, *_ = _build_use_case([emp], total=99, exemplar=exemplar, obra=obra)

    _, total = await use_case.execute()

    assert total == 99


async def test_execute_retorna_lista_de_emprestimo_com_titulo():
    """O retorno é uma lista de EmprestimoComTitulo."""
    emp = _make_emprestimo()
    exemplar = _make_exemplar(id=emp.exemplar_id)
    obra = _make_obra()
    use_case, *_ = _build_use_case([emp], exemplar=exemplar, obra=obra)

    result, _ = await use_case.execute()

    assert len(result) == 1
    assert isinstance(result[0], EmprestimoComTitulo)


# ---------------------------------------------------------------------------
# Testes de enriquecimento com titulo_obra
# ---------------------------------------------------------------------------


async def test_enriquecimento_titulo_obra_correto():
    """titulo_obra deve refletir o título da obra do exemplar."""
    emp = _make_emprestimo()
    exemplar = _make_exemplar(id=emp.exemplar_id, obra_id=_OBRA_ID)
    obra = _make_obra(id=_OBRA_ID, titulo="Memórias Póstumas")
    use_case, _, ex_repo, ob_repo = _build_use_case([emp], exemplar=exemplar, obra=obra)

    result, _ = await use_case.execute()

    assert result[0].titulo_obra == "Memórias Póstumas"


async def test_enriquecimento_exemplar_nao_encontrado_usa_titulo_desconhecido():
    """Quando exemplar não existe, titulo_obra deve ser 'Obra desconhecida'."""
    emp = _make_emprestimo()
    # exemplar_repo returns None
    use_case, *_ = _build_use_case([emp], exemplar=None, obra=None)

    result, _ = await use_case.execute()

    assert result[0].titulo_obra == _TITULO_DESCONHECIDO


async def test_enriquecimento_obra_nao_encontrada_usa_titulo_desconhecido():
    """Quando exemplar existe mas a obra não, titulo_obra deve ser 'Obra desconhecida'."""
    emp = _make_emprestimo()
    exemplar = _make_exemplar(id=emp.exemplar_id)
    # obra_repo returns None
    use_case, *_ = _build_use_case([emp], exemplar=exemplar, obra=None)

    result, _ = await use_case.execute()

    assert result[0].titulo_obra == _TITULO_DESCONHECIDO


async def test_exemplar_repo_chamado_com_exemplar_id_correto():
    """exemplar_repo.get_by_id deve ser chamado com o exemplar_id do empréstimo."""
    exemplar_id = uuid4()
    emp = _make_emprestimo(exemplar_id=exemplar_id)
    exemplar = _make_exemplar(id=exemplar_id)
    obra = _make_obra()
    use_case, _, ex_repo, _ = _build_use_case([emp], exemplar=exemplar, obra=obra)

    await use_case.execute()

    ex_repo.get_by_id.assert_awaited_once_with(exemplar_id)


async def test_obra_repo_chamado_com_obra_id_do_exemplar():
    """obra_repo.get_by_id deve ser chamado com o obra_id resolvido via exemplar."""
    obra_id = uuid4()
    emp = _make_emprestimo()
    exemplar = _make_exemplar(id=emp.exemplar_id, obra_id=obra_id)
    obra = _make_obra(id=obra_id)
    use_case, _, _, ob_repo = _build_use_case([emp], exemplar=exemplar, obra=obra)

    await use_case.execute()

    ob_repo.get_by_id.assert_awaited_once_with(obra_id)


async def test_obra_repo_nao_chamado_quando_exemplar_nao_encontrado():
    """obra_repo.get_by_id não deve ser chamado se exemplar for None."""
    emp = _make_emprestimo()
    use_case, _, _, ob_repo = _build_use_case([emp], exemplar=None, obra=None)

    await use_case.execute()

    ob_repo.get_by_id.assert_not_called()


# ---------------------------------------------------------------------------
# Testes com múltiplos itens
# ---------------------------------------------------------------------------


async def test_multiplos_emprestimos_cada_um_enriquecido():
    """Cada empréstimo é enriquecido com o título correto."""
    obra_id_a = uuid4()
    obra_id_b = uuid4()
    exemplar_id_a = uuid4()
    exemplar_id_b = uuid4()

    emp_a = _make_emprestimo(exemplar_id=exemplar_id_a)
    emp_b = _make_emprestimo(exemplar_id=exemplar_id_b)

    exemplar_a = _make_exemplar(id=exemplar_id_a, obra_id=obra_id_a)
    exemplar_b = _make_exemplar(id=exemplar_id_b, obra_id=obra_id_b)

    obra_a = _make_obra(id=obra_id_a, titulo="Título A")
    obra_b = _make_obra(id=obra_id_b, titulo="Título B")

    emp_repo = _build_emprestimo_repo([emp_a, emp_b], total=2)

    # ex_repo returns exemplar based on id argument
    ex_repo = MagicMock()
    ex_repo.get_by_id = AsyncMock(
        side_effect=lambda id: exemplar_a if id == exemplar_id_a else exemplar_b
    )

    # ob_repo returns obra based on id argument
    ob_repo = MagicMock()
    ob_repo.get_by_id = AsyncMock(
        side_effect=lambda id: obra_a if id == obra_id_a else obra_b
    )

    use_case = ListarEmprestimosUseCase(emp_repo, ex_repo, ob_repo)

    result, total = await use_case.execute()

    assert total == 2
    assert len(result) == 2
    assert result[0].titulo_obra == "Título A"
    assert result[1].titulo_obra == "Título B"


async def test_multiplos_emprestimos_ordem_preservada():
    """A ordem dos empréstimos retornados pelo repositório é preservada."""
    ids = [uuid4() for _ in range(3)]
    emprestimos = [_make_emprestimo(id=i) for i in ids]

    emp_repo = _build_emprestimo_repo(emprestimos)
    ex_repo = _build_exemplar_repo(None)  # all titles will be desconhecido
    ob_repo = _build_obra_repo(None)
    use_case = ListarEmprestimosUseCase(emp_repo, ex_repo, ob_repo)

    result, _ = await use_case.execute()

    assert [r.id for r in result] == ids


# ---------------------------------------------------------------------------
# Testes de preservação de campos
# ---------------------------------------------------------------------------


async def test_emprestimo_com_titulo_preserva_todos_os_campos():
    """EmprestimoComTitulo deve conter exatamente os mesmos valores do Emprestimo original."""
    now = datetime.now(timezone.utc)
    emp_id = uuid4()
    exemplar_id = uuid4()
    leitor_id = uuid4()
    devolucao = now - timedelta(days=1)

    emp = Emprestimo(
        id=emp_id,
        exemplar_id=exemplar_id,
        leitor_id=leitor_id,
        data_checkout=now - timedelta(days=10),
        data_prevista=now + timedelta(days=4),
        data_devolucao=devolucao,
        renovacoes=2,
        status="devolvido",
    )

    exemplar = _make_exemplar(id=exemplar_id)
    obra = _make_obra(titulo="Quincas Borba")
    use_case, *_ = _build_use_case([emp], exemplar=exemplar, obra=obra)

    result, _ = await use_case.execute()
    dto = result[0]

    assert dto.id == emp_id
    assert dto.exemplar_id == exemplar_id
    assert dto.leitor_id == leitor_id
    assert dto.data_checkout == emp.data_checkout
    assert dto.data_prevista == emp.data_prevista
    assert dto.data_devolucao == devolucao
    assert dto.renovacoes == 2
    assert dto.status == "devolvido"
    assert dto.titulo_obra == "Quincas Borba"
