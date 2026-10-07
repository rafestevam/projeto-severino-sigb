"""Router FastAPI para os endpoints de exemplares.

Thin adapter: recebe parâmetros HTTP, instancia serviços via Depends e
devolve a resposta serializada. Nenhuma lógica de negócio aqui.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import get_current_user
from app.adapters.api.schemas.exemplar import BaixarExemplarIn, ExemplarOut
from app.adapters.repositories.sqlalchemy_emprestimo_repository import (
    SQLAlchemyEmprestimoRepository,
)
from app.adapters.repositories.sqlalchemy_exemplar_repository import (
    SQLAlchemyExemplarRepository,
)
from app.adapters.repositories.sqlalchemy_inventario_log_repository import (
    SQLAlchemyInventarioLogRepository,
)
from app.adapters.repositories.sqlalchemy_obra_repository import (
    SQLAlchemyObraRepository,
)
from app.domain.exceptions import (
    ExemplarJaBaixadoError,
    ExemplarJaEmprestadoError,
    ExemplarNotFoundError,
)
from app.infrastructure.database import get_db_session
from app.infrastructure.etiqueta_pdf_service import EtiquetaPdfService
from app.use_cases.baixar_exemplar import BaixarExemplarUseCase

exemplares_router = APIRouter(prefix="/exemplares", tags=["exemplares"])


@exemplares_router.get("/by-qr/{codigo_qr}", response_model=ExemplarOut)
async def obter_exemplar_por_qr(
    codigo_qr: str,
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> ExemplarOut:
    """US-023 — Retorna um exemplar pelo código QR, enriquecido com titulo_obra."""
    exemplar_repo = SQLAlchemyExemplarRepository(session)
    exemplar = await exemplar_repo.get_by_codigo_qr(codigo_qr)
    if exemplar is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exemplar não encontrado: {codigo_qr}",
        )
    obra_repo = SQLAlchemyObraRepository(session)
    obra = await obra_repo.get_by_id(exemplar.obra_id)
    titulo_obra = obra.titulo if obra else None
    out = ExemplarOut.model_validate(exemplar)
    out.titulo_obra = titulo_obra
    return out


@exemplares_router.get("/{id}", response_model=ExemplarOut)
async def obter_exemplar(
    id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> ExemplarOut:
    """Retorna um exemplar pelo ID."""
    repo = SQLAlchemyExemplarRepository(session)
    exemplar = await repo.get_by_id(id)
    if exemplar is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exemplar não encontrado: {id}",
        )
    return ExemplarOut.model_validate(exemplar)


@exemplares_router.post("/{id}/baixar", response_model=ExemplarOut)
async def baixar_exemplar(
    id: UUID,
    body: BaixarExemplarIn,
    session: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> ExemplarOut:
    """US-020 — Marca um exemplar como baixado (danificado ou extraviado)."""
    exemplar_repo = SQLAlchemyExemplarRepository(session)
    emprestimo_repo = SQLAlchemyEmprestimoRepository(session)
    inventario_log_repo = SQLAlchemyInventarioLogRepository(session)

    use_case = BaixarExemplarUseCase(
        exemplar_repo=exemplar_repo,
        emprestimo_repo=emprestimo_repo,
        inventario_log_repo=inventario_log_repo,
    )

    try:
        exemplar = await use_case.execute(
            exemplar_id=id,
            motivo=body.motivo,
            operador_keycloak_id=current_user,
        )
    except ExemplarNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ExemplarJaEmprestadoError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ExemplarJaBaixadoError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return ExemplarOut.model_validate(exemplar)


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
