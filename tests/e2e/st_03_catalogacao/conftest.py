"""
Fixtures e fakes específicos para os testes e2e do ST-03 — Catalogação.

Fornece:
  - FakeIsbnGateway: substituto in-process para o gateway externo de ISBN.
  - isbn_gateway_override: fixture que injeta o fake via dependency_overrides da FastAPI.
  - obra_factory: persiste uma Obra diretamente no banco de teste.
  - exemplar_factory: persiste um Exemplar diretamente no banco de teste.
  - auth_headers_leitor: token de leitor (sem role adequada — espera 403 nos endpoints de escrita).
  - auth_headers_operador e auth_headers_admin já são herdados do conftest pai.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.exemplar import ExemplarModel
from app.adapters.repositories.models.obra import ObraModel


# ─── FakeIsbnGateway ─────────────────────────────────────────────────────────

class FakeIsbnGateway:
    """
    Implementação fake do gateway de ISBN para testes e2e.

    Controla o comportamento por ISBN:
      - ISBN "9788535902778" → retorna metadados completos (hit)
      - ISBN "0000000000000" → retorna schema vazio (empty)
      - qualquer outro      → retorna schema vazio (fallback)

    Não implementa a ABC real porque esta ainda não existe no codebase;
    quando IsbnGateway for adicionada à camada de domínio/infraestrutura,
    esta classe deverá estendê-la.
    """

    METADATA_BY_ISBN: dict[str, dict[str, Any]] = {
        "9788535902778": {
            "titulo": "Dom Casmurro",
            "autores": ["Machado de Assis"],
            "editora": "Ática",
            "ano": 1899,
            "capa_url": "https://example.com/dom-casmurro.jpg",
        },
    }

    async def buscar(self, isbn: str) -> dict[str, Any]:
        """Retorna metadados controlados para o ISBN fornecido."""
        return self.METADATA_BY_ISBN.get(isbn, {
            "titulo": None,
            "autores": None,
            "editora": None,
            "ano": None,
            "capa_url": None,
        })


# ─── Fixture de override do gateway ──────────────────────────────────────────

@pytest.fixture()
def isbn_gateway_override():
    """
    Sobrescreve a dependência FastAPI do gateway de ISBN pelo FakeIsbnGateway.

    Quando o gateway real for implementado e registrado como dependência FastAPI,
    esta fixture deve atualizar o import abaixo para apontar para a função de
    dependência correta (ex: get_isbn_gateway).
    """
    try:
        from app.main import app

        # Tenta importar a dependência real; se não existir, o override é no-op.
        from app.infrastructure.isbn_gateway import get_isbn_gateway  # type: ignore[import]

        fake = FakeIsbnGateway()
        app.dependency_overrides[get_isbn_gateway] = lambda: fake  # type: ignore[attr-defined]
        yield fake
        app.dependency_overrides.pop(get_isbn_gateway, None)
    except ImportError:
        # Gateway ainda não implementado — yielda o fake para uso direto nos testes
        yield FakeIsbnGateway()


# ─── Factories de persistência ────────────────────────────────────────────────

async def obra_factory(
    db_session: AsyncSession,
    *,
    isbn: str | None = None,
    titulo: str = "Obra de Teste",
    autores: list[str] | None = None,
    editora: str = "Editora Teste",
    ano: int = 2024,
    categoria: str = "Ficção",
    capa_url: str | None = None,
) -> ObraModel:
    """Persiste uma Obra no banco de teste e retorna o modelo salvo."""
    model = ObraModel(
        id=uuid.uuid4(),
        isbn=isbn,
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
    codigo_qr: str,
    localizacao_estante: str = "A-01",
) -> ExemplarModel:
    """Persiste um Exemplar no banco de teste e retorna o modelo salvo."""
    model = ExemplarModel(
        id=uuid.uuid4(),
        obra_id=obra_id,
        codigo_qr=codigo_qr,
        estado="disponivel",
        localizacao_estante=localizacao_estante,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(model)
    await db_session.flush()
    await db_session.refresh(model)
    return model


# ─── Auth headers para leitor (role insuficiente) ────────────────────────────

@pytest.fixture()
def auth_headers_leitor() -> dict[str, str]:
    """
    Token JWT simulado para o perfil `leitor`.
    Usado para validar que endpoints de escrita retornam 403 para este perfil.
    """
    return {"Authorization": "Bearer test-token-leitor"}
