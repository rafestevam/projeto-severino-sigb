"""Router FastAPI para os endpoints de exemplares.

Thin adapter: recebe parâmetros HTTP, instancia serviços via Depends e
devolve a resposta serializada. Nenhuma lógica de negócio aqui.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import get_current_user
from app.adapters.repositories.sqlalchemy_exemplar_repository import (
    SQLAlchemyExemplarRepository,
)
from app.infrastructure.database import get_db_session
from app.infrastructure.etiqueta_pdf_service import EtiquetaPdfService

exemplares_router = APIRouter(prefix="/exemplares", tags=["exemplares"])


@exemplares_router.get("/{codigo_qr}/etiqueta.pdf")
async def gerar_etiqueta_pdf(
    codigo_qr: str,
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> Response:
    """US-010 — Gera e retorna o PDF de etiqueta QR Code para o exemplar informado."""
    repo = SQLAlchemyExemplarRepository(session)
    exemplar = await repo.get_by_codigo_qr(codigo_qr)
    if exemplar is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exemplar não encontrado: {codigo_qr}",
        )
    pdf_bytes = EtiquetaPdfService().gerar([exemplar])
    return Response(content=pdf_bytes, media_type="application/pdf")
