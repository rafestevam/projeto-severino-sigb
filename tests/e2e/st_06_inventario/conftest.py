"""
Fixtures e factories para os testes e2e do ST-06 — Inventário e Gestão.

Princípios aplicados (seguindo o padrão ST-04/ST-05):
  - Factories são funções async puras — apenas persistência de estado, sem asserções,
    sem acoplamento ao pytest. Podem ser importadas diretamente nos arquivos de teste.
  - Fixtures de conveniência retornam as funções factory como callables injetáveis pelo pytest,
    permitindo que os testes as chamem como `await obra_factory(db_session, ...)`.
  - `obra_com_exemplar` e `exemplar_baixado_factory` são expostos como fixtures que
    retornam callables — a sessão/cliente são capturados via closure.
  - Sem asserções internas: assert pertence ao teste.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Callable

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.models.exemplar import ExemplarModel
from app.adapters.repositories.models.inventario_log import InventarioLogModel

# ─── Reexporta factories do ST-04 (disponíveis para importação direta) ─────────
from tests.e2e.st_04_circulacao.conftest import (  # noqa: F401 — reexport
    emprestimo_factory as _emprestimo_factory,
    exemplar_factory as _exemplar_factory,
    leitor_factory as _leitor_factory,
    obra_factory as _obra_factory,
)


# ─── Gerador de ISBN-13 válido ────────────────────────────────────────────────

def _gerar_isbn13() -> str:
    """
    Gera um ISBN-13 válido com prefixo 978 e check digit correto.

    O endpoint POST /api/obras valida o ISBN com checksum; ISBNs sintéticos
    arbitrários (ex: 'E2E-xxx') são rejeitados com 422.
    """
    prefix = [9, 7, 8]
    body = [random.randint(0, 9) for _ in range(9)]
    digits = prefix + body
    total = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    check = (10 - total % 10) % 10
    return "".join(str(d) for d in digits) + str(check)


# ─── Fixtures que expõem as factories do ST-04 como callables pytest ──────────
#
# Esses fixtures retornam a função factory pura, permitindo que o teste chame:
#   obra = await obra_factory(db_session, titulo="Minha Obra")
# sem precisar importar diretamente do conftest do ST-04.

@pytest.fixture()
def obra_factory() -> Callable:
    """Retorna a factory de obras para uso em testes como callable."""
    return _obra_factory


@pytest.fixture()
def exemplar_factory() -> Callable:
    """Retorna a factory de exemplares para uso em testes como callable."""
    return _exemplar_factory


@pytest.fixture()
def leitor_factory() -> Callable:
    """Retorna a factory de leitores para uso em testes como callable."""
    return _leitor_factory


@pytest.fixture()
def emprestimo_factory() -> Callable:
    """Retorna a factory de empréstimos para uso em testes como callable."""
    return _emprestimo_factory


# ─── Factory: inventario_log ──────────────────────────────────────────────────

async def inventario_log_factory(
    db_session: AsyncSession,
    *,
    exemplar_id: uuid.UUID,
    operador_keycloak_id: str = "test-token-admin",
    acao: str = "encontrado",
) -> InventarioLogModel:
    """Persiste um InventarioLog diretamente no banco. Sem asserções."""
    model = InventarioLogModel(
        id=uuid.uuid4(),
        exemplar_id=exemplar_id,
        operador_keycloak_id=operador_keycloak_id,
        acao=acao,
    )
    db_session.add(model)
    await db_session.flush()
    await db_session.refresh(model)
    return model


# ─── Factory: exemplar já baixado ────────────────────────────────────────────

async def _exemplar_baixado_factory(
    db_session: AsyncSession,
    *,
    obra_id: uuid.UUID,
    localizacao: str = "A-01",
    motivo_baixa: str = "danificado",
    codigo_qr: str | None = None,
) -> ExemplarModel:
    """Persiste ExemplarModel com estado='baixado' e motivo_baixa. Sem asserções."""
    model = ExemplarModel(
        id=uuid.uuid4(),
        obra_id=obra_id,
        codigo_qr=codigo_qr or f"QR-BAIXADO-{uuid.uuid4().hex[:8].upper()}",
        estado="baixado",
        localizacao_estante=localizacao,
        motivo_baixa=motivo_baixa,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(model)
    await db_session.flush()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture()
async def exemplar_baixado_factory(db_session: AsyncSession) -> Callable:
    """
    Fixture que retorna a factory de exemplares baixados com db_session pré-injetado.

    Uso no teste:
        ex = await exemplar_baixado_factory(obra_id=obra.id, motivo_baixa="danificado")
    """
    async def _factory(
        *,
        obra_id: uuid.UUID,
        localizacao: str = "A-01",
        motivo_baixa: str = "danificado",
        codigo_qr: str | None = None,
    ) -> ExemplarModel:
        return await _exemplar_baixado_factory(
            db_session,
            obra_id=obra_id,
            localizacao=localizacao,
            motivo_baixa=motivo_baixa,
            codigo_qr=codigo_qr,
        )
    return _factory


# ─── Fixture: obra_com_exemplar via factories de banco ───────────────────────
#
# Usar factories de banco (em vez de chamadas HTTP) para criar obra + exemplar,
# contornando a limitação de isolamento SAVEPOINT que impede que uma sessão HTTP
# veja writes de outra sessão HTTP dentro da mesma transação de teste.
#
# A fixture retorna um callable que produz um dict compatível com o formato
# JSON que a API retornaria — permitindo que os testes usem obra["id"],
# exemplar["codigo_qr"], exemplar["id"], etc., sem alteração.

@pytest_asyncio.fixture()
async def obra_com_exemplar(
    db_session: AsyncSession,
) -> Callable:
    """
    Fixture que retorna um callable para criar obra + exemplar diretamente no banco.

    Retorna dicts no mesmo formato que a API retornaria, de modo que os testes
    possam usar obra["id"], exemplar["codigo_qr"], exemplar["id"] etc.

    Uso no teste:
        obra, exemplar = await obra_com_exemplar()
        obra, exemplar = await obra_com_exemplar("B-02")
    """
    async def _factory(localizacao: str = "A-01") -> tuple[dict, dict]:
        obra_model = await _obra_factory(
            db_session,
            titulo=f"Obra E2E {uuid.uuid4().hex[:6]}",
            isbn=_gerar_isbn13(),
        )
        exemplar_model = await _exemplar_factory(
            db_session,
            obra_id=obra_model.id,
            localizacao_estante=localizacao,
        )
        obra_dict = {
            "id": str(obra_model.id),
            "isbn": obra_model.isbn,
            "titulo": obra_model.titulo,
            "autores": obra_model.autores,
            "editora": obra_model.editora,
            "ano": obra_model.ano,
            "capa_url": obra_model.capa_url,
            "categoria": obra_model.categoria,
            "created_at": obra_model.created_at.isoformat(),
        }
        exemplar_dict = {
            "id": str(exemplar_model.id),
            "obra_id": str(exemplar_model.obra_id),
            "codigo_qr": exemplar_model.codigo_qr,
            "estado": exemplar_model.estado,
            "localizacao_estante": exemplar_model.localizacao_estante,
            "created_at": exemplar_model.created_at.isoformat(),
            "origem": getattr(exemplar_model, "origem", None),
            "motivo_baixa": getattr(exemplar_model, "motivo_baixa", None),
        }
        return obra_dict, exemplar_dict

    return _factory
