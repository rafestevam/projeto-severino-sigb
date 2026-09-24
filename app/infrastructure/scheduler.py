from __future__ import annotations

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.adapters.repositories.sqlalchemy_emprestimo_repository import (
    SQLAlchemyEmprestimoRepository,
)
from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.notificacao_gateway_stub import NotificacaoGatewayStub
from app.use_cases.marcar_atrasados import MarcarAtrasadosUseCase

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def executar_job_marcar_atrasados() -> int:
    """Executes the daily overdue marking job inside a fresh DB session."""
    logger.info("Iniciando execução do job diário de marcar atrasados.")
    async with AsyncSessionLocal() as session:
        async with session.begin():
            emprestimo_repo = SQLAlchemyEmprestimoRepository(session)
            notificacao_gateway = NotificacaoGatewayStub()
            use_case = MarcarAtrasadosUseCase(
                emprestimo_repo=emprestimo_repo,
                notificacao_gateway=notificacao_gateway,
            )
            total = await use_case.execute()
            logger.info("Job de marcar atrasados concluído. Total marcados: %d", total)
            return total


def setup_scheduler() -> AsyncIOScheduler:
    """Configures scheduled background jobs."""
    if not scheduler.get_job("marcar_emprestimos_atrasados"):
        scheduler.add_job(
            executar_job_marcar_atrasados,
            trigger=CronTrigger(hour=0, minute=0),
            id="marcar_emprestimos_atrasados",
            name="Marcar empréstimos atrasados diariamente",
            replace_existing=True,
        )
    return scheduler
