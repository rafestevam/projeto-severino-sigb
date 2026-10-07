"""Router FastAPI para os endpoints de inventário (US-019).

Thin adapter: recebe parâmetros HTTP, instancia serviços via Depends e
devolve a resposta serializada. Nenhuma lógica de negócio aqui.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import get_current_user
from app.adapters.api.schemas.inventario import (
    ExemplarScanOut,
    InventarioScanIn,
    InventarioScanOut,
)
from app.adapters.repositories.sqlalchemy_exemplar_repository import (
    SQLAlchemyExemplarRepository,
)
from app.adapters.repositories.sqlalchemy_inventario_log_repository import (
    SQLAlchemyInventarioLogRepository,
)
from app.infrastructure.database import get_db_session
from app.use_cases.realizar_inventario import RealizarInventarioUseCase

inventario_router = APIRouter(prefix="/inventario", tags=["inventario"])


@inventario_router.post("/scan", response_model=InventarioScanOut)
async def scan_inventario(
    body: InventarioScanIn,
    session: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> InventarioScanOut:
    """US-019 — Realiza inventário das estantes por bipagem de QR Code."""
    exemplar_repo = SQLAlchemyExemplarRepository(session)
    inventario_log_repo = SQLAlchemyInventarioLogRepository(session)

    use_case = RealizarInventarioUseCase(
        exemplar_repo=exemplar_repo,
        inventario_log_repo=inventario_log_repo,
    )

    resultado = await use_case.execute(
        codigos_qr=body.codigos_qr,
        localizacao=body.localizacao,
        operador_keycloak_id=current_user,
    )

    return InventarioScanOut(
        encontrados=[
            ExemplarScanOut(codigo_qr=e.codigo_qr, estado=e.estado)
            for e in resultado.encontrados
        ],
        nao_bipados=[
            ExemplarScanOut(codigo_qr=e.codigo_qr, estado=e.estado)
            for e in resultado.nao_bipados
        ],
        nao_esperados=[
            ExemplarScanOut(codigo_qr=e.codigo_qr, estado=e.estado)
            for e in resultado.nao_esperados
        ],
    )
