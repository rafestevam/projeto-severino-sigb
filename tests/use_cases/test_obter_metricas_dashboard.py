"""
Testes unitários para ObterMetricasDashboardUseCase e
ListarEmprestimosAtrasadosUseCase (US-021).

Estratégia: AsyncMock para todos os repositórios — sem banco de dados,
SQLAlchemy ou FastAPI.

Casos cobertos:
  - Happy path: todos os campos de MetricasDashboard calculados corretamente.
  - taxa_perdas é 0.0 quando não há exemplares extraviados.
  - taxa_perdas é 0.0 quando total_exemplares == 0 (evita divisão por zero).
  - taxa_perdas calculada corretamente com valores conhecidos.
  - top_obras_emprestadas contém no máximo 10 itens (controlado pelo repo).
  - ListarEmprestimosAtrasadosUseCase delega ao repositório e retorna lista.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.entities.emprestimo import Emprestimo
from app.domain.entities.leitor import Leitor
from app.domain.entities.obra import Obra
from app.use_cases.obter_metricas_dashboard import (
    ExemplaresEstado,
    ListarEmprestimosAtrasadosUseCase,
    MetricasDashboard,
    ObterMetricasDashboardUseCase,
    ObraTopEmprestimos,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_obra(total_emprestimos: int = 5) -> Obra:
    return Obra(
        id=uuid4(),
        isbn=None,
        titulo="Dom Casmurro",
        autores=["Machado de Assis"],
        editora="Editora X",
        ano=1899,
        capa_url="",
        categoria="Literatura",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        total_emprestimos=total_emprestimos,
    )


def _make_leitor() -> Leitor:
    return Leitor(
        id=uuid4(),
        nome="Ana Lima",
        cpf_hash=Leitor.hash_cpf("12345678900"),
        telefone="11999999999",
        email="ana@email.com",
        ativo=True,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_emprestimo(status: str = "atrasado") -> Emprestimo:
    return Emprestimo(
        id=uuid4(),
        exemplar_id=uuid4(),
        leitor_id=uuid4(),
        data_checkout=datetime(2025, 1, 1, tzinfo=timezone.utc),
        data_prevista=datetime(2025, 1, 15, tzinfo=timezone.utc),
        data_devolucao=None,
        renovacoes=0,
        status=status,
    )


def _build_obra_repo(
    *,
    count: int = 10,
    top_obras: list[Obra] | None = None,
) -> MagicMock:
    repo = MagicMock()
    repo.count_all = AsyncMock(return_value=count)
    repo.list_top_emprestadas = AsyncMock(return_value=top_obras or [])
    return repo


def _build_exemplar_repo(
    *,
    count: int = 50,
    contagens_estado: dict | None = None,
    extraviados: int = 0,
    doacoes: int = 0,
) -> MagicMock:
    repo = MagicMock()
    repo.count_all = AsyncMock(return_value=count)
    repo.count_by_estado = AsyncMock(
        return_value=contagens_estado
        or {"disponivel": 40, "emprestado": 8, "baixado": 2}
    )
    repo.count_baixados_por_motivo = AsyncMock(return_value=extraviados)
    repo.count_by_origem = AsyncMock(return_value=doacoes)
    return repo


def _build_leitor_repo(*, leitores: list[Leitor] | None = None) -> MagicMock:
    repo = MagicMock()
    repo.list_ativos = AsyncMock(return_value=leitores or [])
    return repo


def _build_emprestimo_repo(*, items: list[Emprestimo] | None = None) -> MagicMock:
    repo = MagicMock()
    repo.list_filtered = AsyncMock(return_value=(items or [], len(items or [])))
    return repo


def _build_dashboard_use_case(
    *,
    count_obras: int = 10,
    count_exemplares: int = 50,
    leitores_ativos: list[Leitor] | None = None,
    contagens_estado: dict | None = None,
    top_obras: list[Obra] | None = None,
    extraviados: int = 0,
    doacoes: int = 0,
) -> tuple[ObterMetricasDashboardUseCase, MagicMock, MagicMock, MagicMock]:
    obra_repo = _build_obra_repo(count=count_obras, top_obras=top_obras)
    exemplar_repo = _build_exemplar_repo(
        count=count_exemplares,
        contagens_estado=contagens_estado,
        extraviados=extraviados,
        doacoes=doacoes,
    )
    leitor_repo = _build_leitor_repo(leitores=leitores_ativos)
    use_case = ObterMetricasDashboardUseCase(obra_repo, exemplar_repo, leitor_repo)
    return use_case, obra_repo, exemplar_repo, leitor_repo


# ---------------------------------------------------------------------------
# Happy path — MetricasDashboard
# ---------------------------------------------------------------------------


async def test_dashboard_retorna_metricas_dashboard():
    use_case, _, _, _ = _build_dashboard_use_case()

    result = await use_case.execute()

    assert isinstance(result, MetricasDashboard)


async def test_dashboard_total_obras_correto():
    use_case, _, _, _ = _build_dashboard_use_case(count_obras=7)

    result = await use_case.execute()

    assert result.total_obras == 7


async def test_dashboard_total_exemplares_correto():
    use_case, _, _, _ = _build_dashboard_use_case(count_exemplares=33)

    result = await use_case.execute()

    assert result.total_exemplares == 33


async def test_dashboard_total_leitores_ativos_correto():
    leitores = [_make_leitor(), _make_leitor(), _make_leitor()]
    use_case, _, _, _ = _build_dashboard_use_case(leitores_ativos=leitores)

    result = await use_case.execute()

    assert result.total_leitores_ativos == 3


async def test_dashboard_exemplares_por_estado_correto():
    contagens = {"disponivel": 30, "emprestado": 15, "baixado": 5}
    use_case, _, _, _ = _build_dashboard_use_case(contagens_estado=contagens)

    result = await use_case.execute()

    assert result.exemplares_por_estado.disponivel == 30
    assert result.exemplares_por_estado.emprestado == 15
    assert result.exemplares_por_estado.baixado == 5


async def test_dashboard_top_obras_tem_campos_corretos():
    obra = _make_obra(total_emprestimos=12)
    use_case, _, _, _ = _build_dashboard_use_case(top_obras=[obra])

    result = await use_case.execute()

    assert len(result.top_obras_emprestadas) == 1
    item = result.top_obras_emprestadas[0]
    assert item.obra_id == obra.id
    assert item.titulo == obra.titulo
    assert item.total_emprestimos == 12


async def test_dashboard_top_obras_e_lista_de_obra_top_emprestimos():
    use_case, _, _, _ = _build_dashboard_use_case(top_obras=[_make_obra()])

    result = await use_case.execute()

    assert all(isinstance(o, ObraTopEmprestimos) for o in result.top_obras_emprestadas)


async def test_dashboard_total_doacoes_correto():
    use_case, _, _, _ = _build_dashboard_use_case(doacoes=8)

    result = await use_case.execute()

    assert result.total_doacoes == 8


# ---------------------------------------------------------------------------
# taxa_perdas
# ---------------------------------------------------------------------------


async def test_taxa_perdas_zero_quando_sem_extraviados():
    use_case, _, _, _ = _build_dashboard_use_case(
        count_exemplares=100, extraviados=0
    )

    result = await use_case.execute()

    assert result.taxa_perdas == 0.0


async def test_taxa_perdas_zero_quando_total_exemplares_zero():
    use_case, _, _, _ = _build_dashboard_use_case(
        count_exemplares=0, extraviados=0
    )

    result = await use_case.execute()

    assert result.taxa_perdas == 0.0


async def test_taxa_perdas_calculada_corretamente():
    use_case, _, _, _ = _build_dashboard_use_case(
        count_exemplares=100, extraviados=5
    )

    result = await use_case.execute()

    assert result.taxa_perdas == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# ListarEmprestimosAtrasadosUseCase
# ---------------------------------------------------------------------------


async def test_listar_atrasados_retorna_lista_de_emprestimos():
    emp1 = _make_emprestimo("atrasado")
    emp2 = _make_emprestimo("atrasado")
    emprestimo_repo = _build_emprestimo_repo(items=[emp1, emp2])
    use_case = ListarEmprestimosAtrasadosUseCase(emprestimo_repo)

    result = await use_case.execute()

    assert len(result) == 2
    assert all(isinstance(e, Emprestimo) for e in result)


async def test_listar_atrasados_chama_list_filtered_com_status_atrasado():
    emprestimo_repo = _build_emprestimo_repo()
    use_case = ListarEmprestimosAtrasadosUseCase(emprestimo_repo)

    await use_case.execute()

    call_kwargs = emprestimo_repo.list_filtered.await_args.kwargs
    assert call_kwargs.get("status") == "atrasado"


async def test_listar_atrasados_retorna_lista_vazia_quando_nenhum():
    emprestimo_repo = _build_emprestimo_repo(items=[])
    use_case = ListarEmprestimosAtrasadosUseCase(emprestimo_repo)

    result = await use_case.execute()

    assert result == []
