from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.adapters.repositories.sqlalchemy_emprestimo_repository import (
    SQLAlchemyEmprestimoRepository,
)
from app.adapters.repositories.sqlalchemy_exemplar_repository import (
    SQLAlchemyExemplarRepository,
)
from app.adapters.repositories.sqlalchemy_leitor_repository import (
    SQLAlchemyLeitorRepository,
)
from app.adapters.repositories.sqlalchemy_notificacao_log_repository import (
    SQLAlchemyNotificacaoLogRepository,
)
from app.adapters.repositories.sqlalchemy_obra_repository import (
    SQLAlchemyObraRepository,
)
from app.infrastructure.database import AsyncSessionLocal
from app.use_cases.enviar_lembretes import EnviarLembretesUseCase
from app.use_cases.marcar_atrasados import MarcarAtrasadosUseCase

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def executar_job_marcar_atrasados() -> int:
    """Executes the daily overdue marking job inside a fresh DB session."""
    logger.info("Iniciando execução do job diário de marcar atrasados.")
    async with AsyncSessionLocal() as session:
        async with session.begin():
            from app.infrastructure.whatsapp_notificacao_gateway import (
                WhatsAppNotificacaoGateway,
            )

            emprestimo_repo = SQLAlchemyEmprestimoRepository(session)
            log_repo = SQLAlchemyNotificacaoLogRepository(session)
            notificacao_gateway = WhatsAppNotificacaoGateway(log_repo=log_repo)
            use_case = MarcarAtrasadosUseCase(
                emprestimo_repo=emprestimo_repo,
                notificacao_gateway=notificacao_gateway,
            )
            total = await use_case.execute()
            logger.info("Job de marcar atrasados concluído. Total marcados: %d", total)
            return total


async def executar_job_lembretes_devolucao() -> int:
    """Executes the daily D-1 reminder job inside a fresh DB session."""
    logger.info("Iniciando execução do job diário de lembretes de devolução.")
    async with AsyncSessionLocal() as session:
        async with session.begin():
            from app.infrastructure.whatsapp_notificacao_gateway import (
                WhatsAppNotificacaoGateway,
            )

            emprestimo_repo = SQLAlchemyEmprestimoRepository(session)
            leitor_repo = SQLAlchemyLeitorRepository(session)
            exemplar_repo = SQLAlchemyExemplarRepository(session)
            obra_repo = SQLAlchemyObraRepository(session)
            log_repo = SQLAlchemyNotificacaoLogRepository(session)
            notificacao_gateway = WhatsAppNotificacaoGateway(log_repo=log_repo)
            use_case = EnviarLembretesUseCase(
                emprestimo_repo=emprestimo_repo,
                leitor_repo=leitor_repo,
                exemplar_repo=exemplar_repo,
                obra_repo=obra_repo,
                notificacao_gateway=notificacao_gateway,
            )
            total = await use_case.execute()
            logger.info("Job de lembretes concluído. Total enviados: %d", total)
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
    if not scheduler.get_job("enviar_lembretes_devolucao"):
        scheduler.add_job(
            executar_job_lembretes_devolucao,
            trigger=CronTrigger(hour=8, minute=0),
            id="enviar_lembretes_devolucao",
            name="Enviar lembretes de devolução D-1",
            replace_existing=True,
        )
    return scheduler
