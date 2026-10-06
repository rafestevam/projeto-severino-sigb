"""Logging stub implementation of NotificacaoGateway for integration tests.

Unlike NotificacaoGatewayStub, this stub writes every notification attempt
to the notificacao_log table via SQLAlchemyNotificacaoLogRepository so that
e2e tests can verify audit entries via db_session.

Usage in tests:
    Override the `get_notificacao_gateway` FastAPI dependency with a closure
    that returns a NotificacaoGatewayLoggingStub backed by the test session.
"""
from __future__ import annotations

import logging
from uuid import UUID

from app.adapters.repositories.sqlalchemy_notificacao_log_repository import (
    SQLAlchemyNotificacaoLogRepository,
)
from app.domain.gateways.notificacao_gateway import NotificacaoGateway

logger = logging.getLogger(__name__)


class NotificacaoGatewayLoggingStub(NotificacaoGateway):
    """Test stub that records every enviar() call to notificacao_log.

    Parameters
    ----------
    log_repo:
        Repository used to persist each notification attempt.
    raise_on_first:
        When True, raises RuntimeError on the *first* call to enviar() and then
        acts normally. Useful for testing partial-failure scenarios (e.g. LEM-E2E-009).
    error_message:
        Custom error message used when raise_on_first=True. Defaults to
        "Timeout ao conectar" to match the test plan description.
    """

    def __init__(
        self,
        log_repo: SQLAlchemyNotificacaoLogRepository,
        raise_on_first: bool = False,
        error_message: str = "Timeout ao conectar",
    ) -> None:
        self._log_repo = log_repo
        self._raise_on_first = raise_on_first
        self._error_message = error_message
        self._call_count = 0

    async def enviar(self, destino: str, template: str, params: dict) -> None:
        """Log the notification and optionally raise on the first call."""
        self._call_count += 1

        if self._raise_on_first and self._call_count == 1:
            leitor_id = self._extract_leitor_id(params)
            await self._log_repo.registrar(
                leitor_id=leitor_id,
                template=template,
                status="erro",
                erro=self._error_message,
            )
            raise RuntimeError(self._error_message)

        leitor_id = self._extract_leitor_id(params)
        await self._log_repo.registrar(
            leitor_id=leitor_id,
            template=template,
            status="enviado",
            erro=None,
        )
        logger.info(
            "Notificação (logging-stub) | destino=%s | template=%s | params=%s",
            destino,
            template,
            params,
        )

    @staticmethod
    def _extract_leitor_id(params: dict) -> UUID:
        """Extract leitor_id UUID from params dict, falling back to a nil UUID."""
        raw = params.get("leitor_id")
        if raw:
            try:
                return UUID(str(raw))
            except ValueError:
                pass
        return UUID("00000000-0000-0000-0000-000000000000")
