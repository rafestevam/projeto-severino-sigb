from datetime import datetime
from uuid import uuid4

from app.domain.entities import Emprestimo


def test_emprestimo_instantiation_sets_all_attributes() -> None:
    emprestimo_id = uuid4()
    exemplar_id = uuid4()
    leitor_id = uuid4()
    data_checkout = datetime(2024, 1, 10, 14, 30)
    data_prevista = datetime(2024, 1, 17, 14, 30)
    data_devolucao = datetime(2024, 1, 15, 10, 0)

    emprestimo = Emprestimo(
        id=emprestimo_id,
        exemplar_id=exemplar_id,
        leitor_id=leitor_id,
        data_checkout=data_checkout,
        data_prevista=data_prevista,
        data_devolucao=data_devolucao,
        renovacoes=1,
        status="ativo",
    )

    assert emprestimo.id == emprestimo_id
    assert emprestimo.exemplar_id == exemplar_id
    assert emprestimo.leitor_id == leitor_id
    assert emprestimo.data_checkout == data_checkout
    assert emprestimo.data_prevista == data_prevista
    assert emprestimo.data_devolucao == data_devolucao
    assert emprestimo.renovacoes == 1
    assert emprestimo.status == "ativo"
