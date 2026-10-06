"""Concrete implementation of NotificacaoGateway for WhatsApp Business Cloud API.

Calls the Meta Graph API, implements exponential-backoff retry on 5xx/timeout,
and records every attempt in notificacao_log via SQLAlchemyNotificacaoLogRepository.
"""
from __future__ import annotations

import asyncio
import logging
import os
from uuid import UUID

import httpx

from app.adapters.repositories.sqlalchemy_notificacao_log_repository import (
    SQLAlchemyNotificacaoLogRepository,
)
from app.domain.gateways.notificacao_gateway import NotificacaoGateway

logger = logging.getLogger(__name__)

_META_API_URL = "https://graph.facebook.com/v19.0/{phone_number_id}/messages"
_MAX_RETRIES = 3
_TIMEOUT_SECONDS = 10


class WhatsAppNotificacaoGateway(NotificacaoGateway):
    """Sends WhatsApp notifications via Meta Business Cloud API with retry + audit log."""

    def __init__(self, log_repo: SQLAlchemyNotificacaoLogRepository) -> None:
        self._log_repo = log_repo
        self._wa_token = os.getenv("WA_TOKEN")
        self._phone_number_id = os.getenv("WA_PHONE_NUMBER_ID")
        if not self._wa_token or not self._phone_number_id:
            raise RuntimeError(
                "WhatsAppNotificacaoGateway requires WA_TOKEN and WA_PHONE_NUMBER_ID "
                "environment variables to be set."
            )

    async def enviar(self, destino: str, template: str, params: dict) -> None:
        """
        Send a WhatsApp template message to *destino*.

        If *destino* is empty or None, returns silently without sending or logging.
        Retries up to _MAX_RETRIES times with exponential backoff (1s, 2s, 4s) on
        HTTP 5xx or timeout. On final failure, logs the error without propagating.
        """
        if not destino:
            return

        payload = self._build_payload(destino, template, params)
        url = _META_API_URL.format(phone_number_id=self._phone_number_id)
        headers = {
            "Authorization": f"Bearer {self._wa_token}",
            "Content-Type": "application/json",
        }

        last_error: str | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=_TIMEOUT_SECONDS,
                    )
                    response.raise_for_status()

                # Success — log and return
                leitor_id = self._extract_leitor_id(params)
                await self._log_repo.registrar(
                    leitor_id=leitor_id,
                    template=template,
                    status="enviado",
                    erro=None,
                )
                return

            except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                last_error = str(exc)
                is_retryable = isinstance(exc, httpx.TimeoutException) or (
                    isinstance(exc, httpx.HTTPStatusError)
                    and exc.response.status_code >= 500
                )
                if is_retryable and attempt < _MAX_RETRIES - 1:
                    wait = 2 ** attempt  # 1s, 2s (third attempt uses no wait)
                    logger.warning(
                        "WhatsApp API tentativa %d/%d falhou para %s: %s. Aguardando %ds.",
                        attempt + 1,
                        _MAX_RETRIES,
                        destino,
                        last_error,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    break

            except Exception as exc:
                last_error = str(exc)
                logger.exception("Erro inesperado ao enviar notificação para %s", destino)
                break

        # All attempts exhausted — log error silently
        leitor_id = self._extract_leitor_id(params)
        logger.error(
            "Falha ao enviar notificação WhatsApp para %s após %d tentativas: %s",
            destino,
            _MAX_RETRIES,
            last_error,
        )
        await self._log_repo.registrar(
            leitor_id=leitor_id,
            template=template,
            status="erro",
            erro=last_error,
        )

    # ── private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _build_payload(destino: str, template: str, params: dict) -> dict:
        """Build Meta API message payload from template name and parameters."""
        components = []
        if params:
            body_params = [
                {"type": "text", "text": str(v)}
                for v in params.values()
            ]
            components.append({"type": "body", "parameters": body_params})

        return {
            "messaging_product": "whatsapp",
            "to": destino,
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": "pt_BR"},
                "components": components,
            },
        }

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
