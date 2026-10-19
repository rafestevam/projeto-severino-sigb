"""Testes unitários para o read model DisponibilidadeObra (US-028/US-029)."""
from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.entities.disponibilidade_obra import DisponibilidadeObra


@pytest.mark.parametrize(
    ("disponiveis", "emprestados", "disponivel"),
    [(1, 0, True), (2, 5, True), (0, 3, False), (0, 0, False)],
)
def test_disponivel_quando_ha_ao_menos_um_exemplar_livre(
    disponiveis: int, emprestados: int, disponivel: bool
) -> None:
    assert DisponibilidadeObra(uuid4(), disponiveis, emprestados).disponivel is disponivel


def test_tem_exemplares_ativos_falso_sem_nenhum_exemplar() -> None:
    assert DisponibilidadeObra(uuid4(), 0, 0).tem_exemplares_ativos is False


def test_tem_exemplares_ativos_verdadeiro_com_emprestados() -> None:
    assert DisponibilidadeObra(uuid4(), 0, 1).tem_exemplares_ativos is True


def test_e_imutavel() -> None:
    d = DisponibilidadeObra(uuid4(), 1, 0)
    with pytest.raises(AttributeError):
        d.disponiveis = 2  # type: ignore[misc]
