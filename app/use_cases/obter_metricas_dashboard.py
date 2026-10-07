from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.emprestimo import Emprestimo
from app.domain.repositories.emprestimo_repository import EmprestimoRepository
from app.domain.repositories.exemplar_repository import ExemplarRepository
from app.domain.repositories.leitor_repository import LeitorRepository
from app.domain.repositories.obra_repository import ObraRepository


@dataclass
class ExemplaresEstado:
    disponivel: int
    emprestado: int
    baixado: int


@dataclass
class ObraTopEmprestimos:
    obra_id: UUID
    titulo: str
    total_emprestimos: int


@dataclass
class MetricasDashboard:
    total_obras: int
    total_exemplares: int
    total_leitores_ativos: int
    exemplares_por_estado: ExemplaresEstado
    top_obras_emprestadas: list[ObraTopEmprestimos]
    taxa_perdas: float          # baixas com motivo "extraviado" / total exemplares
    total_doacoes: int          # exemplares com origem = "doacao"


class ObterMetricasDashboardUseCase:
    """US-021 — Retorna métricas agregadas do acervo para o dashboard.

    Não expõe dados pessoais de leitores; toda serialização sensível ocorre
    nos schemas Pydantic do router.
    """

    def __init__(
        self,
        obra_repo: ObraRepository,
        exemplar_repo: ExemplarRepository,
        leitor_repo: LeitorRepository,
    ) -> None:
        self._obra_repo = obra_repo
        self._exemplar_repo = exemplar_repo
        self._leitor_repo = leitor_repo

    async def execute(self) -> MetricasDashboard:
        total_obras = await self._obra_repo.count_all()
        total_exemplares = await self._exemplar_repo.count_all()
        leitores_ativos = await self._leitor_repo.list_ativos()
        total_leitores_ativos = len(leitores_ativos)

        contagens_estado = await self._exemplar_repo.count_by_estado()
        exemplares_por_estado = ExemplaresEstado(
            disponivel=contagens_estado.get("disponivel", 0),
            emprestado=contagens_estado.get("emprestado", 0),
            baixado=contagens_estado.get("baixado", 0),
        )

        top_obras_raw = await self._obra_repo.list_top_emprestadas(limit=10)
        top_obras_emprestadas = [
            ObraTopEmprestimos(
                obra_id=o.id,
                titulo=o.titulo,
                total_emprestimos=o.total_emprestimos,
            )
            for o in top_obras_raw
        ]

        extraviados = await self._exemplar_repo.count_baixados_por_motivo("extraviado")
        taxa_perdas = extraviados / total_exemplares if total_exemplares > 0 else 0.0

        total_doacoes = await self._exemplar_repo.count_by_origem("doacao")

        return MetricasDashboard(
            total_obras=total_obras,
            total_exemplares=total_exemplares,
            total_leitores_ativos=total_leitores_ativos,
            exemplares_por_estado=exemplares_por_estado,
            top_obras_emprestadas=top_obras_emprestadas,
            taxa_perdas=taxa_perdas,
            total_doacoes=total_doacoes,
        )


class ListarEmprestimosAtrasadosUseCase:
    """US-021 — Retorna a lista de empréstimos com status 'atrasado'.

    Delega ao repositório sem lógica de negócio adicional. A serialização
    sem dados pessoais é responsabilidade do schema Pydantic no router.
    """

    def __init__(self, emprestimo_repo: EmprestimoRepository) -> None:
        self._emprestimo_repo = emprestimo_repo

    async def execute(self) -> list[Emprestimo]:
        items, _ = await self._emprestimo_repo.list_filtered(status="atrasado", page_size=1000)
        return items
