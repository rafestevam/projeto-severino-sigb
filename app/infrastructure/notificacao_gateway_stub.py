"""Stub implementation of NotificacaoGateway.

The real WhatsApp integration is post-MVP. This stub logs the notification
parameters so the rest of the circulation flow can be exercised without an
external messaging service.
"""
from __future__ import annotations

import logging

from app.domain.gateways.notificacao_gateway import NotificacaoGateway

logger = logging.getLogger(__name__)


class NotificacaoGatewayStub(NotificacaoGateway):
    """No-op gateway that logs notifications instead of delivering them."""

    async def enviar(self, destino: str, template: str, params: dict) -> None:
        """Log the notification payload without contacting any external service."""
        logger.info(
            "Notificação (stub) | destino=%s | template=%s | params=%s",
            destino,
            template,
            params,
        )
