"""Router FastAPI para os endpoints de catalogação de obras e do OPAC.

Thin adapter: recebe parâmetros HTTP, instancia use cases via Depends e
devolve a resposta serializada. Nenhuma lógica de negócio aqui.

As rotas `/publico` (US-028/US-029) não dependem de get_current_user e
devolvem apenas schemas `*PublicaOut`, sem dados sensíveis.
"""
from __future__ import annotations

from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import get_current_user
from app.adapters.api.schemas.exemplar import ExemplarBatchIn, ExemplarOut
from app.adapters.api.schemas.isbn_metadata import IsbnMetadataOut
from app.adapters.api.schemas.obra import (
    ObraIn,
    ObraListOut,
    ObraOut,
    ObraPublicaDetalheOut,
    ObraPublicaListOut,
)
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
from app.use_cases.listar_catalogo_publico import ListarCatalogoPublicoUseCase
from app.use_cases.listar_obras import ListarObrasUseCase
from app.use_cases.obter_obra_publica import ObterObraPublicaUseCase

obras_router = APIRouter(prefix="/obras", tags=["obras"])

# Disponibilidade com até 1 min de atraso é aceitável no catálogo público e
# alivia a API durante a busca "em tempo real".
_CACHE_CATALOGO_PUBLICO = "public, max-age=60"


# Rotas públicas declaradas antes de qualquer `/obras/{id}` para que
# "publico" nunca seja interpretado como UUID.
@obras_router.get("/publico", response_model=ObraPublicaListOut)
async def listar_catalogo_publico(
    response: Response,
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    session: AsyncSession = Depends(get_db_session),
) -> ObraPublicaListOut:
    """US-028 — Catálogo público: busca por título, autor ou categoria (sem login)."""
    use_case = ListarCatalogoPublicoUseCase(
        SQLAlchemyObraRepository(session), SQLAlchemyExemplarRepository(session)
    )
    pagina = await use_case.execute(termo=q, page=page, page_size=page_size)
    response.headers["Cache-Control"] = _CACHE_CATALOGO_PUBLICO
    return ObraPublicaListOut.de_pagina(pagina)


@obras_router.get("/{obra_id}/publico", response_model=ObraPublicaDetalheOut)
async def obter_obra_publica(
    obra_id: UUID,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> ObraPublicaDetalheOut:
    """US-029 — Detalhes públicos da obra com disponibilidade e ranking (sem login)."""
    use_case = ObterObraPublicaUseCase(
        SQLAlchemyObraRepository(session), SQLAlchemyExemplarRepository(session)
    )
    try:
        detalhe = await use_case.execute(obra_id)
    except ObraNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Obra não encontrada",
        ) from exc
    response.headers["Cache-Control"] = _CACHE_CATALOGO_PUBLICO
    return ObraPublicaDetalheOut.de_detalhe(detalhe)


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
        metadados = await use_case.execute(isbn)
    return IsbnMetadataOut.model_validate(metadados)


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
