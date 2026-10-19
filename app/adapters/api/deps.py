from __future__ import annotations

import base64
import json
import os

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.sqlalchemy_leitor_repository import (
    SQLAlchemyLeitorRepository,
)
from app.domain.entities.leitor import Leitor
from app.domain.gateways.notificacao_gateway import NotificacaoGateway
from app.infrastructure.database import get_db_session

_DEV_MODE = os.getenv("DEV_MODE", "").lower() in ("1", "true", "yes")


def get_current_user(authorization: str | None = Header(None)) -> str:
    # Em modo de desenvolvimento, qualquer token (ou nenhum) é aceito.
    if _DEV_MODE:
        if authorization and authorization.startswith("Bearer "):
            return authorization.split(" ", 1)[1]
        return "dev-user"

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


def _claims_do_token(token: str) -> dict:
    """Decodifica o payload do JWT.

    ATENÇÃO: a assinatura NÃO é verificada (enhancement 003). Uma claim pode ser
    forjada até que a validação contra o Keycloak seja implementada, por isso a
    reserva online não deve ir a produção antes disso (decisão D2 do ST-08).
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        ) from exc
    if not isinstance(claims, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    return claims


async def get_leitor_autenticado(
    token: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Leitor:
    """Resolve o Leitor do usuário autenticado pela claim `email` (decisão D1 do ST-08).

    Só e-mails verificados pelo Keycloak são aceitos: com o auto-registro aberto,
    um e-mail não verificado permitiria se passar pelo leitor dono do endereço.
    """
    claims = _claims_do_token(token)
    email = claims.get("email")
    leitor = (
        await SQLAlchemyLeitorRepository(session).get_by_email(email)
        if claims.get("email_verified") is True and isinstance(email, str) and email.strip()
        else None
    )
    if leitor is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nenhum cadastro de leitor vinculado a este usuário",
        )
    return leitor


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
