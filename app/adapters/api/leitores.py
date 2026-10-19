"""Router FastAPI para os endpoints de leitores.

Thin adapter: recebe parâmetros HTTP, instancia use cases via Depends e
devolve a resposta serializada. Nenhuma lógica de negócio aqui.

`POST /leitores` é público (pré-cadastro pelo OPAC, US-030); as demais rotas
exigem autenticação de balcão.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import get_current_user
from app.adapters.api.schemas.leitor import (
    LeitorOut,
    LeitorPreCadastroIn,
    LeitorPreCadastroOut,
)
from app.adapters.repositories.sqlalchemy_leitor_repository import (
    SQLAlchemyLeitorRepository,
)
from app.domain.entities.leitor import Leitor
from app.domain.exceptions import (
    CpfInvalidoError,
    LeitorJaCadastradoError,
    LeitorNaoEncontradoError,
)
from app.infrastructure.database import get_db_session
from app.use_cases.ativar_leitor import AtivarLeitorUseCase
from app.use_cases.pre_cadastrar_leitor import DadosPreCadastro, PreCadastrarLeitorUseCase

leitores_router = APIRouter(prefix="/leitores", tags=["leitores"])


@leitores_router.get("", response_model=LeitorOut)
async def buscar_leitor_por_cpf(
    cpf: str = Query(..., description="CPF do leitor em plaintext, com ou sem máscara"),
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
            detail="Leitor com CPF informado não encontrado",
        )
    return LeitorOut.model_validate(leitor)


@leitores_router.post(
    "", response_model=LeitorPreCadastroOut, status_code=status.HTTP_201_CREATED
)
async def pre_cadastrar_leitor(
    body: LeitorPreCadastroIn,
    session: AsyncSession = Depends(get_db_session),
) -> LeitorPreCadastroOut:
    """US-030 — Pré-cadastro público: cria o leitor pendente de ativação no balcão."""
    use_case = PreCadastrarLeitorUseCase(SQLAlchemyLeitorRepository(session))
    dados = DadosPreCadastro(
        nome=body.nome,
        cpf=body.cpf,
        telefone=body.telefone,
        email=body.email,
    )
    try:
        await use_case.execute(dados)
    except CpfInvalidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="CPF inválido",
        ) from exc
    except LeitorJaCadastradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um cadastro para este CPF. Procure o balcão da biblioteca.",
        ) from exc
    return LeitorPreCadastroOut()


@leitores_router.patch("/{leitor_id}/ativar", response_model=LeitorOut)
async def ativar_leitor(
    leitor_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _: str = Depends(get_current_user),
) -> LeitorOut:
    """US-030 — Operador ativa um leitor pré-cadastrado."""
    use_case = AtivarLeitorUseCase(SQLAlchemyLeitorRepository(session))
    try:
        leitor = await use_case.execute(leitor_id)
    except LeitorNaoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return LeitorOut.model_validate(leitor)
