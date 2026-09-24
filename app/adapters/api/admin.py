from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import get_current_user
from app.adapters.api.schemas.configuracao import (
    ConfiguracaoListOut,
    ConfiguracaoOut,
    ConfiguracaoUpdateIn,
)
from app.adapters.repositories.models.configuracao import ConfiguracaoModel
from app.adapters.repositories.sqlalchemy_configuracao_service import (
    ConfiguracaoServiceImpl,
)
from app.infrastructure.database import get_db_session

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/configuracao", response_model=ConfiguracaoListOut)
async def listar_configuracoes(
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> ConfiguracaoListOut:
    """US-035 — Lista todas as configurações do sistema."""
    result = await session.execute(
        select(ConfiguracaoModel).order_by(ConfiguracaoModel.chave)
    )
    models = result.scalars().all()
    return ConfiguracaoListOut(
        items=[
            ConfiguracaoOut(chave=m.chave, valor=m.valor)
            for m in models
        ]
    )


@admin_router.put("/configuracao/{chave}", response_model=ConfiguracaoOut)
async def atualizar_configuracao(
    chave: str,
    body: ConfiguracaoUpdateIn,
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> ConfiguracaoOut:
    """US-035 — Atualiza ou define o valor de uma configuração do sistema."""
    result = await session.execute(
        select(ConfiguracaoModel).where(ConfiguracaoModel.chave == chave)
    )
    config = result.scalar_one_or_none()

    if config is None:
        config = ConfiguracaoModel(
            id=uuid4(),
            chave=chave,
            valor=body.valor,
            updated_at=datetime.now(timezone.utc),
        )
        session.add(config)
    else:
        config.valor = body.valor
        config.updated_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(config)

    return ConfiguracaoOut(chave=config.chave, valor=config.valor)
