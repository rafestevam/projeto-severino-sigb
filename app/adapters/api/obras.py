"""Router FastAPI para os endpoints de catalogação de obras.

Thin adapter: recebe parâmetros HTTP, instancia use cases via Depends e
devolve a resposta serializada. Nenhuma lógica de negócio aqui.
"""
from __future__ import annotations

from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import get_current_user
from app.adapters.api.schemas.exemplar import ExemplarBatchIn, ExemplarOut
from app.adapters.api.schemas.isbn_metadata import IsbnMetadataOut
from app.adapters.api.schemas.obra import ObraIn, ObraListOut, ObraOut
from app.adapters.repositories.sqlalchemy_exemplar_repository import (
    SQLAlchemyExemplarRepository,
)
from app.adapters.repositories.sqlalchemy_obra_repository import (
    SQLAlchemyObraRepository,
)
from app.domain.exceptions import DuplicateIsbnError, ObraNotFoundError
from app.infrastructure.database import get_db_session
from app.infrastructure.isbn_gateway_impl import IsbnGatewayImpl
from app.use_cases.adicionar_exemplares import AdicionarExemplaresUseCase
from app.use_cases.buscar_metadados_isbn import BuscarMetadadosIsbnUseCase
from app.use_cases.cadastrar_obra import CadastrarObraUseCase
from app.use_cases.listar_obras import ListarObrasUseCase

obras_router = APIRouter(prefix="/obras", tags=["obras"])


@obras_router.post("", response_model=ObraOut, status_code=status.HTTP_201_CREATED)
async def cadastrar_obra(
    body: ObraIn,
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> ObraOut:
    """US-009 — Cadastra uma nova obra na biblioteca."""
    repo = SQLAlchemyObraRepository(session)
    use_case = CadastrarObraUseCase(repo)
    try:
        obra = await use_case.execute(body)
    except DuplicateIsbnError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"isbn: {exc.isbn} já cadastrado",
        ) from exc
    return ObraOut.model_validate(obra)


@obras_router.get("", response_model=ObraListOut)
async def listar_obras(
    titulo: str | None = Query(default=None),
    autor: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> ObraListOut:
    """US-009 — Lista obras com paginação e filtros opcionais."""
    repo = SQLAlchemyObraRepository(session)
    use_case = ListarObrasUseCase(repo)
    obras, total = await use_case.execute(
        titulo=titulo,
        autor=autor,
        categoria=categoria,
        page=page,
        page_size=page_size,
    )
    return ObraListOut(
        items=[ObraOut.model_validate(o) for o in obras],
        total=total,
        page=page,
        page_size=page_size,
    )


@obras_router.post("/isbn/{isbn}", response_model=IsbnMetadataOut)
async def buscar_metadados_isbn(
    isbn: str,
    _: str = Depends(get_current_user),
) -> IsbnMetadataOut:
    """US-008 — Busca metadados de uma obra por ISBN consultando Open Library → Google Books → CBL."""
    async with httpx.AsyncClient() as http_client:
        gateway = IsbnGatewayImpl(http_client)
        use_case = BuscarMetadadosIsbnUseCase(gateway)
        return await use_case.execute(isbn)


@obras_router.post(
    "/{obra_id}/exemplares",
    response_model=list[ExemplarOut],
    status_code=status.HTTP_201_CREATED,
)
async def adicionar_exemplares(
    obra_id: UUID,
    body: ExemplarBatchIn,
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> list[ExemplarOut]:
    """US-010 — Cria N exemplares para a obra informada com códigos QR sequenciais."""
    obra_repo = SQLAlchemyObraRepository(session)
    exemplar_repo = SQLAlchemyExemplarRepository(session)
    use_case = AdicionarExemplaresUseCase(obra_repo, exemplar_repo)
    try:
        exemplares = await use_case.execute(
            obra_id=obra_id,
            quantidade=body.quantidade,
            localizacao_estante=body.localizacao_estante,
        )
    except ObraNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return [ExemplarOut.model_validate(e) for e in exemplares]
