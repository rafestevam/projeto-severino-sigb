from __future__ import annotations

from abc import ABC, abstractmethod


class NotificacaoGateway(ABC):
    """Abstract gateway for sending notifications (e.g. WhatsApp, e-mail)."""

    @abstractmethod
    async def enviar(self, destino: str, template: str, params: dict) -> None:
        """
        Send a notification to the given destination.

        Args:
            destino:  Recipient address (phone number, e-mail, etc.).
            template: Identifier for the message template.
            params:   Template parameters to be interpolated.
        """
