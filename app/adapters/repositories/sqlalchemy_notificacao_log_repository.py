from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.notificacao_log import NotificacaoLogModel


class SQLAlchemyNotificacaoLogRepository:
    """Concrete repository for persisting notification audit log entries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def registrar(
        self,
        leitor_id: UUID,
        template: str,
        status: str,
        erro: str | None,
    ) -> None:
        """Insert a notification log entry and flush to the current transaction."""
        entry = NotificacaoLogModel(
            id=uuid.uuid4(),
            leitor_id=leitor_id,
            template=template,
            status=status,
            erro=erro,
        )
        self._session.add(entry)
        await self._session.flush()
