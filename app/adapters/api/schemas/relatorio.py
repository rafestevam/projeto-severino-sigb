from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ExemplaresEstadoOut(BaseModel):
    disponivel: int
    emprestado: int
    baixado: int


class ObraTopEmprestimosOut(BaseModel):
    obra_id: UUID
    titulo: str
    total_emprestimos: int


class DashboardOut(BaseModel):
    total_obras: int
    total_exemplares: int
    total_leitores_ativos: int
    exemplares_por_estado: ExemplaresEstadoOut
    top_obras_emprestadas: list[ObraTopEmprestimosOut]
    taxa_perdas: float
    total_doacoes: int


class EmprestimoAtrasadoOut(BaseModel):
    """Empréstimo em atraso — sem dados pessoais identificáveis do leitor."""

    id: UUID
    exemplar_id: UUID
    leitor_id: UUID
    data_checkout: datetime
    data_prevista: datetime
    status: str


class EmprestimosAtrasadosListOut(BaseModel):
    items: list[EmprestimoAtrasadoOut]
    total: int
