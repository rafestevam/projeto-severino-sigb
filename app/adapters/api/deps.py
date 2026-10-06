from __future__ import annotations

import os

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.gateways.notificacao_gateway import NotificacaoGateway
from app.infrastructure.database import get_db_session


def get_current_user(authorization: str | None = Header(None)) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header de Autorização ausente",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de token inválido",
        )

    parts = authorization.split(" ")
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de token inválido",
        )

    token = parts[1]
    return token


def get_notificacao_gateway(
    session: AsyncSession = Depends(get_db_session),
) -> NotificacaoGateway:
    """
    Composition-root factory for the NotificacaoGateway dependency.

    Selects the concrete implementation based on runtime configuration:
    - WhatsAppNotificacaoGateway when WA_TOKEN and WA_PHONE_NUMBER_ID are set.
    - NotificacaoGatewayStub otherwise (dev / CI without credentials).

    In integration tests this dependency is overridden via
    app.dependency_overrides[get_notificacao_gateway] — the selection logic
    here is never exercised in that context.
    """
    from app.adapters.repositories.sqlalchemy_notificacao_log_repository import (
        SQLAlchemyNotificacaoLogRepository,
    )

    wa_token = os.getenv("WA_TOKEN")
    wa_phone_number_id = os.getenv("WA_PHONE_NUMBER_ID")

    if wa_token and wa_phone_number_id:
        from app.infrastructure.whatsapp_notificacao_gateway import (
            WhatsAppNotificacaoGateway,
        )
        log_repo = SQLAlchemyNotificacaoLogRepository(session)
        return WhatsAppNotificacaoGateway(log_repo=log_repo)

    from app.infrastructure.notificacao_gateway_stub import NotificacaoGatewayStub
    return NotificacaoGatewayStub()
