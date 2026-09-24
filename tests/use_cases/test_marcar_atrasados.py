"""
Testes unitários para MarcarAtrasadosUseCase.

Estratégia: usar unittest.mock.AsyncMock para mockar EmprestimoRepository
e NotificacaoGateway, sem dependência de banco de dados, SQLAlchemy, APScheduler ou FastAPI.

Casos cobertos:
  - Nenhum empréstimo vencido: retorna 0, não chama save nem enviar.
  - Múltiplos empréstimos vencidos: atualiza status para 'atrasado', salva e envia notificação para cada um.
  - Idempotência: list_ativos_vencidos só retorna 'ativo' vencidos, retornando a contagem processada.
  - Falha no envio de notificação não impede o processamento dos demais empréstimos nem quebra a execução.
  - Notificação enviada com os parâmetros esperados (destino, template, params).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.domain.entities.emprestimo import Emprestimo
from app.use_cases.marcar_atrasados import MarcarAtrasadosUseCase


def _make_emprestimo(
    *,
    id: UUID | None = None,
    exemplar_id: UUID | None = None,
    leitor_id: UUID | None = None,
    status: str = "ativo",
    data_checkout: datetime | None = None,
    data_prevista: datetime | None = None,
) -> Emprestimo:
    now = datetime.now(timezone.utc)
    checkout = data_checkout or (now - timedelta(days=20))
    prevista = data_prevista or (now - timedelta(days=5))
    return Emprestimo(
        id=id or uuid4(),
        exemplar_id=exemplar_id or uuid4(),
        leitor_id=leitor_id or uuid4(),
        data_checkout=checkout,
        data_prevista=prevista,
        data_devolucao=None,
        renovacoes=0,
        status=status,
    )


@pytest.fixture
def emprestimo_repo():
    repo = AsyncMock()
    repo.save = AsyncMock(side_effect=lambda e: e)
    return repo


@pytest.fixture
def notificacao_gateway():
    gateway = AsyncMock()
    gateway.enviar = AsyncMock(return_value=None)
    return gateway


@pytest.fixture
def use_case(emprestimo_repo, notificacao_gateway):
    return MarcarAtrasadosUseCase(
        emprestimo_repo=emprestimo_repo,
        notificacao_gateway=notificacao_gateway,
    )


class TestMarcarAtrasadosUseCase:
    async def test_nenhum_emprestimo_vencido(
        self, use_case, emprestimo_repo, notificacao_gateway
    ):
        emprestimo_repo.list_ativos_vencidos.return_value = []

        total = await use_case.execute()

        assert total == 0
        emprestimo_repo.save.assert_not_called()
        notificacao_gateway.enviar.assert_not_called()

    async def test_marca_multiplos_emprestimos_vencidos(
        self, use_case, emprestimo_repo, notificacao_gateway
    ):
        emp1 = _make_emprestimo()
        emp2 = _make_emprestimo()
        emprestimo_repo.list_ativos_vencidos.return_value = [emp1, emp2]

        total = await use_case.execute()

        assert total == 2
        assert emp1.status == "atrasado"
        assert emp2.status == "atrasado"
        assert emprestimo_repo.save.call_count == 2
        assert notificacao_gateway.enviar.call_count == 2

    async def test_notificacao_enviada_com_parametros_corretos(
        self, use_case, emprestimo_repo, notificacao_gateway
    ):
        emp = _make_emprestimo()
        emprestimo_repo.list_ativos_vencidos.return_value = [emp]

        await use_case.execute()

        notificacao_gateway.enviar.assert_called_once_with(
            destino=str(emp.leitor_id),
            template="emprestimo_atrasado",
            params={
                "emprestimo_id": str(emp.id),
                "exemplar_id": str(emp.exemplar_id),
                "data_prevista": emp.data_prevista.isoformat(),
            },
        )

    async def test_falha_em_notificacao_nao_impede_proximos_emprestimos(
        self, use_case, emprestimo_repo, notificacao_gateway
    ):
        emp1 = _make_emprestimo()
        emp2 = _make_emprestimo()
        emprestimo_repo.list_ativos_vencidos.return_value = [emp1, emp2]

        # Simula erro na primeira notificação
        notificacao_gateway.enviar.side_effect = [
            RuntimeError("WhatsApp error"),
            None,
        ]

        total = await use_case.execute()

        assert total == 2
        assert emp1.status == "atrasado"
        assert emp2.status == "atrasado"
        assert emprestimo_repo.save.call_count == 2
        assert notificacao_gateway.enviar.call_count == 2
