"""
Fixtures e factories específicas para os testes e2e do ST-04 — Circulação.

Fornece:
  - obra_factory: persiste uma Obra diretamente no banco de teste.
  - exemplar_factory: persiste um Exemplar diretamente no banco de teste.
  - leitor_factory: persiste um Leitor ativo diretamente no banco de teste.
  - emprestimo_factory: persiste um Empréstimo com datas controláveis (para cenários de atraso).
  - auth_headers_leitor: token JWT simulado para o perfil `leitor` (sem role de operador).

As fixtures auth_headers_operador e auth_headers_admin são herdadas do conftest pai
(tests/e2e/conftest.py).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.emprestimo import EmprestimoModel
from app.adapters.repositories.models.exemplar import ExemplarModel
from app.adapters.repositories.models.leitor import LeitorModel
from app.adapters.repositories.models.obra import ObraModel
from app.domain.entities.leitor import Leitor


# ─── Factories ────────────────────────────────────────────────────────────────

async def obra_factory(
    db_session: AsyncSession,
    *,
    titulo: str = "Obra de Teste",
    isbn: str | None = None,
    autores: list[str] | None = None,
    editora: str = "Editora Teste",
    ano: int = 2024,
    categoria: str = "Ficção",
    capa_url: str | None = None,
) -> ObraModel:
    """Persiste uma Obra no banco de teste e retorna o modelo salvo.

    Nota: a coluna isbn é NOT NULL no banco (migration 0001). A factory sempre
    gera um ISBN sintético único quando nenhum é fornecido, para respeitar essa
    constraint sem exigir que cada chamador forneça um valor.
    """
    # A migration 0001 define isbn como NOT NULL; gera valor único se não informado.
    isbn_val = isbn if isbn is not None else f"TEST-{uuid.uuid4().hex[:10].upper()}"
    model = ObraModel(
        id=uuid.uuid4(),
        isbn=isbn_val,
        titulo=titulo,
        autores=autores or ["Autor Teste"],
        editora=editora,
        ano=ano,
        capa_url=capa_url,
        categoria=categoria,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(model)
    await db_session.flush()
    await db_session.refresh(model)
    return model


async def exemplar_factory(
    db_session: AsyncSession,
    *,
    obra_id: uuid.UUID,
    codigo_qr: str | None = None,
    estado: str = "disponivel",
    localizacao_estante: str = "A-01",
) -> ExemplarModel:
    """Persiste um Exemplar no banco de teste e retorna o modelo salvo."""
    model = ExemplarModel(
        id=uuid.uuid4(),
        obra_id=obra_id,
        codigo_qr=codigo_qr or f"QR-{uuid.uuid4().hex[:8].upper()}",
        estado=estado,
        localizacao_estante=localizacao_estante,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(model)
    await db_session.flush()
    await db_session.refresh(model)
    return model


async def leitor_factory(
    db_session: AsyncSession,
    *,
    cpf: str | None = None,
    nome: str = "Leitor Teste",
    email: str | None = None,
    telefone: str = "11999990001",
    ativo: bool = True,
) -> LeitorModel:
    """Persiste um Leitor no banco de teste e retorna o modelo salvo."""
    cpf = cpf or str(uuid.uuid4().int)[:11]
    model = LeitorModel(
        id=uuid.uuid4(),
        nome=nome,
        cpf_hash=Leitor.hash_cpf(cpf),
        telefone=telefone,
        email=email or f"leitor_{uuid.uuid4().hex[:6]}@teste.com",
        ativo=ativo,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(model)
    await db_session.flush()
    await db_session.refresh(model)
    return model


async def emprestimo_factory(
    db_session: AsyncSession,
    *,
    exemplar_id: uuid.UUID,
    leitor_id: uuid.UUID,
    data_prevista: datetime | None = None,
    status: str = "ativo",
    renovacoes: int = 0,
) -> EmprestimoModel:
    """Persiste um Empréstimo com datas controláveis no banco de teste."""
    now = datetime.now(timezone.utc)
    model = EmprestimoModel(
        id=uuid.uuid4(),
        exemplar_id=exemplar_id,
        leitor_id=leitor_id,
        data_checkout=now - timedelta(days=14),
        data_prevista=data_prevista or (now + timedelta(days=14)),
        data_devolucao=None,
        renovacoes=renovacoes,
        status=status,
    )
    db_session.add(model)
    await db_session.flush()
    await db_session.refresh(model)
    return model


# ─── Auth headers para leitor (role insuficiente) ────────────────────────────

@pytest.fixture()
def auth_headers_leitor() -> dict[str, str]:
    """
    Token JWT simulado para o perfil `leitor` (sem role de operador).
    Usado para validar que endpoints protegidos retornam 401 sem token adequado.
    """
    return {"Authorization": "Bearer test-token-leitor"}
