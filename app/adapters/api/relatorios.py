"""Router FastAPI para os endpoints de relatórios (US-021).

Thin adapter: recebe parâmetros HTTP, instancia serviços via Depends e
devolve a resposta serializada. Nenhuma lógica de negócio aqui.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import get_current_user
from app.adapters.api.schemas.relatorio import (
    DashboardOut,
    EmprestimoAtrasadoOut,
    EmprestimosAtrasadosListOut,
    ExemplaresEstadoOut,
    ObraTopEmprestimosOut,
)
from app.adapters.repositories.sqlalchemy_emprestimo_repository import (
    SQLAlchemyEmprestimoRepository,
)
from app.adapters.repositories.sqlalchemy_exemplar_repository import (
    SQLAlchemyExemplarRepository,
)
from app.adapters.repositories.sqlalchemy_leitor_repository import (
    SQLAlchemyLeitorRepository,
)
from app.adapters.repositories.sqlalchemy_obra_repository import (
    SQLAlchemyObraRepository,
)
from app.infrastructure.database import get_db_session
from app.use_cases.obter_metricas_dashboard import (
    ListarEmprestimosAtrasadosUseCase,
    ObterMetricasDashboardUseCase,
)

relatorios_router = APIRouter(prefix="/relatorios", tags=["relatorios"])


@relatorios_router.get("/dashboard", response_model=DashboardOut)
async def obter_dashboard(
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> DashboardOut:
    """US-021 — Retorna métricas agregadas do acervo para o dashboard."""
    obra_repo = SQLAlchemyObraRepository(session)
    exemplar_repo = SQLAlchemyExemplarRepository(session)
    leitor_repo = SQLAlchemyLeitorRepository(session)

    use_case = ObterMetricasDashboardUseCase(
        obra_repo=obra_repo,
        exemplar_repo=exemplar_repo,
        leitor_repo=leitor_repo,
    )

    metricas = await use_case.execute()

    return DashboardOut(
        total_obras=metricas.total_obras,
        total_exemplares=metricas.total_exemplares,
        total_leitores_ativos=metricas.total_leitores_ativos,
        exemplares_por_estado=ExemplaresEstadoOut(
            disponivel=metricas.exemplares_por_estado.disponivel,
            emprestado=metricas.exemplares_por_estado.emprestado,
            baixado=metricas.exemplares_por_estado.baixado,
        ),
        top_obras_emprestadas=[
            ObraTopEmprestimosOut(
                obra_id=o.obra_id,
                titulo=o.titulo,
                total_emprestimos=o.total_emprestimos,
            )
            for o in metricas.top_obras_emprestadas
        ],
        taxa_perdas=metricas.taxa_perdas,
        total_doacoes=metricas.total_doacoes,
    )


@relatorios_router.get("/emprestimos-atrasados", response_model=EmprestimosAtrasadosListOut)
async def listar_emprestimos_atrasados(
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> EmprestimosAtrasadosListOut:
    """US-021 — Lista empréstimos em atraso (somente admin)."""
    emprestimo_repo = SQLAlchemyEmprestimoRepository(session)

    use_case = ListarEmprestimosAtrasadosUseCase(emprestimo_repo=emprestimo_repo)
    emprestimos = await use_case.execute()

    items = [
        EmprestimoAtrasadoOut(
            id=e.id,
            exemplar_id=e.exemplar_id,
            leitor_id=e.leitor_id,
            data_checkout=e.data_checkout,
            data_prevista=e.data_prevista,
            status=e.status,
        )
        for e in emprestimos
    ]

    return EmprestimosAtrasadosListOut(items=items, total=len(items))
