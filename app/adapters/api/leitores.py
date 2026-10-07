"""Router FastAPI para os endpoints de leitores.

Thin adapter: recebe parâmetros HTTP, instancia repositórios via Depends e
devolve a resposta serializada. Nenhuma lógica de negócio aqui.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import get_current_user
from app.adapters.api.schemas.leitor import LeitorOut
from app.adapters.repositories.sqlalchemy_leitor_repository import (
    SQLAlchemyLeitorRepository,
)
from app.domain.entities.leitor import Leitor
from app.infrastructure.database import get_db_session

leitores_router = APIRouter(prefix="/leitores", tags=["leitores"])


@leitores_router.get("", response_model=LeitorOut)
async def buscar_leitor_por_cpf(
    cpf: str = Query(..., description="CPF do leitor em plaintext"),
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> LeitorOut:
    """US-023 — Busca leitor pelo CPF (hash SHA-256 calculado aqui).

    Recebe o CPF em plaintext, calcula o hash e delega ao repositório.
    Retorna 404 se o leitor não for encontrado.
    """
    cpf_hash = Leitor.hash_cpf(cpf)
    repo = SQLAlchemyLeitorRepository(session)
    leitor = await repo.get_by_cpf_hash(cpf_hash)
    if leitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Leitor com CPF informado não encontrado",
        )
    return LeitorOut(id=leitor.id, nome=leitor.nome, ativo=leitor.ativo)
