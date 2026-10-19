from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DisponibilidadeObra:
    """Read model: contagem de exemplares ativos (não baixados) de uma obra."""

    obra_id: UUID
    disponiveis: int
    emprestados: int

    @property
    def disponivel(self) -> bool:
        return self.disponiveis > 0

    @property
    def tem_exemplares_ativos(self) -> bool:
        return self.disponiveis + self.emprestados > 0
