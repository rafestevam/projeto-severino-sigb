"""
Fixtures e factories específicas para os testes e2e do ST-05 — Reservas e Notificações.

Fornece:
  - Reexporta obra_factory, exemplar_factory, leitor_factory e emprestimo_factory
    do conftest do ST-04 (evita duplicação).
  - reserva_factory: persiste uma Reserva diretamente no banco com created_at controlável.
  - notificacao_log_factory: persiste um registro de log diretamente (para testes de auditoria).
  - leitor_sem_telefone_factory: atalho que cria leitor com telefone=None.
  - client_com_stub: AsyncClient cujo get_notificacao_gateway é sobreposto por um
    NotificacaoGatewayLoggingStub, permitindo verificação de notificacao_log em testes HTTP.

Princípios observados:
  - Factories manipulam apenas modelos de domínio/repositório — sem lógica de aplicação.
  - O stub de teste mora em tests/, não em app/.
  - client_com_stub não cria sessão extra: delega à mesma db_connection da fixture pai
    para que cada request handler use a transação aninhada do teste.
  - As fixtures auth_headers_* são herdadas de tests/e2e/conftest.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.adapters.repositories.models.notificacao_log import NotificacaoLogModel
from app.adapters.repositories.models.reserva import ReservaModel
from app.adapters.repositories.sqlalchemy_notificacao_log_repository import (
    SQLAlchemyNotificacaoLogRepository,
)

# ─── Reexporta factories do ST-04 ────────────────────────────────────────────
from tests.e2e.st_04_circulacao.conftest import (  # noqa: F401 — reexport
    emprestimo_factory,
    exemplar_factory,
    leitor_factory,
    obra_factory,
)
from tests.infrastructure.notificacao_gateway_logging_stub import (
    NotificacaoGatewayLoggingStub,
)


# ─── Factory de reservas ──────────────────────────────────────────────────────

async def reserva_factory(
    db_session: AsyncSession,
    *,
    obra_id: uuid.UUID,
    leitor_id: uuid.UUID,
    status: str = "aguardando",
    created_at: datetime | None = None,
) -> ReservaModel:
    """Persiste uma Reserva diretamente no banco e retorna o modelo salvo.

    O parâmetro created_at é controlável para simular cenários de fila FIFO.
    """
    model = ReservaModel(
        id=uuid.uuid4(),
        obra_id=obra_id,
        leitor_id=leitor_id,
        status=status,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db_session.add(model)
    await db_session.flush()
    await db_session.refresh(model)
    return model


# ─── Factory de notificacao_log ───────────────────────────────────────────────

async def notificacao_log_factory(
    db_session: AsyncSession,
    *,
    leitor_id: uuid.UUID,
    template: str,
    status: str = "enviado",
    erro: str | None = None,
) -> NotificacaoLogModel:
    """Persiste um registro de NotificacaoLog diretamente no banco."""
    model = NotificacaoLogModel(
        id=uuid.uuid4(),
        leitor_id=leitor_id,
        template=template,
        status=status,
        erro=erro,
    )
    db_session.add(model)
    await db_session.flush()
    await db_session.refresh(model)
    return model


# ─── Factory de leitor sem telefone ──────────────────────────────────────────

async def leitor_sem_telefone_factory(
    db_session: AsyncSession,
    *,
    nome: str = "Leitor Sem Telefone",
    email: str | None = None,
) -> object:
    """Atalho que cria leitor com telefone=None (cenário de silêncio de notificação)."""
    from app.adapters.repositories.models.leitor import LeitorModel
    from app.domain.entities.leitor import Leitor

    model = LeitorModel(
        id=uuid.uuid4(),
        nome=nome,
        cpf_hash=Leitor.hash_cpf(str(uuid.uuid4().int)[:11]),
        telefone=None,
        email=email or f"semfone_{uuid.uuid4().hex[:6]}@teste.com",
        ativo=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(model)
    await db_session.flush()
    await db_session.refresh(model)
    return model


# ─── Helpers internos ────────────────────────────────────────────────────────

def _build_stub_overrides(
    db_connection: AsyncConnection,
    shared_session: AsyncSession,
    raise_on_first: bool = False,
    error_message: str = "Timeout ao conectar",
) -> tuple[NotificacaoGatewayLoggingStub, object, object]:
    """
    Constrói o stub e os dois overrides de FastAPI dependency (get_db e get_gateway).

    Usa shared_session tanto para o stub quanto para os handlers HTTP, garantindo
    que escritas do stub (notificacao_log) e do handler (update de reserva) estejam
    na mesma sessão e portanto visíveis para db_session.execute() no teste.

    Retorna (stub, _override_get_db, _override_get_gateway).
    """
    log_repo = SQLAlchemyNotificacaoLogRepository(shared_session)
    stub = NotificacaoGatewayLoggingStub(
        log_repo=log_repo,
        raise_on_first=raise_on_first,
        error_message=error_message,
    )

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        # Todos os handlers HTTP deste teste usam a mesma sessão transacional,
        # garantindo visibilidade imediata de todas as escritas (stub + handler).
        yield shared_session

    def _override_get_gateway() -> NotificacaoGatewayLoggingStub:
        return stub

    return stub, _override_get_db, _override_get_gateway


# ─── Client com stub injetado (sucesso) ──────────────────────────────────────

@pytest_asyncio.fixture()
async def client_com_stub(
    db_connection: AsyncConnection,
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient com NotificacaoGatewayLoggingStub que registra envios bem-sucedidos.

    O stub e todos os handlers HTTP compartilham db_session (a sessão transacional
    do teste), garantindo que escritas do stub sejam imediatamente visíveis para
    asserções feitas via db_session.execute() no corpo do teste.

    Responsabilidade única: compor a app com o stub de sucesso.
    """
    from app.adapters.api.deps import get_notificacao_gateway
    from app.infrastructure.database import get_db_session
    from app.main import app

    _, _override_get_db, _override_get_gateway = _build_stub_overrides(
        db_connection, db_session
    )

    app.dependency_overrides[get_db_session] = _override_get_db
    app.dependency_overrides[get_notificacao_gateway] = _override_get_gateway

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


# ─── Client com stub injetado (falha na primeira chamada) ────────────────────

@pytest_asyncio.fixture()
async def client_com_stub_falho(
    db_connection: AsyncConnection,
    db_session: AsyncSession,
) -> AsyncGenerator[tuple[AsyncClient, AsyncSession], None]:
    """
    AsyncClient com NotificacaoGatewayLoggingStub configurado para falhar na 1ª chamada.

    Yields (client, db_session) — use db_session para verificar que o log de erro
    foi gravado na mesma transação do teste.

    Use em LOG-E2E-007: verifica que o check-in retorna 200 mesmo com falha de gateway,
    e que o log de erro é persistido.
    """
    from app.adapters.api.deps import get_notificacao_gateway
    from app.infrastructure.database import get_db_session
    from app.main import app

    _, _override_get_db, _override_get_gateway = _build_stub_overrides(
        db_connection, db_session, raise_on_first=True, error_message="Erro simulado"
    )

    app.dependency_overrides[get_db_session] = _override_get_db
    app.dependency_overrides[get_notificacao_gateway] = _override_get_gateway

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac, db_session

    app.dependency_overrides.clear()
