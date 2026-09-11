"""
Seed script — popula o banco com dados de exemplo para desenvolvimento.

Uso:
    DATABASE_URL=postgresql+asyncpg://libsys:changeme@localhost:5432/libsysdb \
        python scripts/seed_dev.py

O script é idempotente em relação a erros de unicidade: se os registros já
existirem (mesmo isbn / codigo_qr / cpf_hash), o script imprime um aviso e
encerra sem lançar exceção.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

# Garante que o pacote 'app' seja encontrado quando o script é executado
# diretamente a partir da raiz do projeto.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.adapters.repositories.models.emprestimo import EmprestimoModel  # noqa: E402
from app.adapters.repositories.models.exemplar import ExemplarModel  # noqa: E402
from app.adapters.repositories.models.leitor import LeitorModel  # noqa: E402
from app.adapters.repositories.models.obra import ObraModel  # noqa: E402
from app.adapters.repositories.models.reserva import ReservaModel  # noqa: E402
from app.domain.entities.leitor import Leitor  # noqa: E402

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://libsys:changeme@db:5432/libsysdb"
)

now = datetime.now(tz=timezone.utc)


# ─── Dados de exemplo ────────────────────────────────────────────────────────

OBRAS = [
    ObraModel(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        isbn="9788535902778",
        titulo="Dom Casmurro",
        autores=["Machado de Assis"],
        editora="Ática",
        ano=1899,
        capa_url=None,
        categoria="Literatura Brasileira",
        created_at=now,
    ),
    ObraModel(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        isbn="9788525415066",
        titulo="O Cortiço",
        autores=["Aluísio Azevedo"],
        editora="Ática",
        ano=1890,
        capa_url=None,
        categoria="Literatura Brasileira",
        created_at=now,
    ),
    ObraModel(
        id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        isbn="9788532513403",
        titulo="Vidas Secas",
        autores=["Graciliano Ramos"],
        editora="Record",
        ano=1938,
        capa_url=None,
        categoria="Literatura Brasileira",
        created_at=now,
    ),
    ObraModel(
        id=uuid.UUID("00000000-0000-0000-0000-000000000004"),
        isbn="9788535911497",
        titulo="Memórias Póstumas de Brás Cubas",
        autores=["Machado de Assis"],
        editora="Ática",
        ano=1881,
        capa_url=None,
        categoria="Literatura Brasileira",
        created_at=now,
    ),
    ObraModel(
        id=uuid.UUID("00000000-0000-0000-0000-000000000005"),
        isbn="9788573262162",
        titulo="Grande Sertão: Veredas",
        autores=["João Guimarães Rosa"],
        editora="Nova Fronteira",
        ano=1956,
        capa_url=None,
        categoria="Literatura Brasileira",
        created_at=now,
    ),
]

EXEMPLARES = [
    ExemplarModel(
        id=uuid.UUID(f"00000000-0000-0000-0001-{i:012d}"),
        obra_id=OBRAS[(i - 1) // 2].id,
        codigo_qr=f"QR-{i:04d}",
        estado="disponivel",
        localizacao_estante=f"A-{i:02d}",
        created_at=now,
    )
    for i in range(1, 11)
]

LEITORES = [
    LeitorModel(
        id=uuid.UUID(f"00000000-0000-0000-0002-{i:012d}"),
        nome=nome,
        cpf_hash=Leitor.hash_cpf(cpf),
        telefone=telefone,
        email=email,
        ativo=True,
        created_at=now,
    )
    for i, (nome, cpf, telefone, email) in enumerate(
        [
            ("Ana Souza", "11122233344", "11999990001", "ana@example.com"),
            ("Bruno Lima", "22233344455", "11999990002", "bruno@example.com"),
            ("Carla Neves", "33344455566", None, "carla@example.com"),
        ],
        start=1,
    )
]

EMPRESTIMOS = [
    EmprestimoModel(
        id=uuid.UUID(f"00000000-0000-0000-0003-{i:012d}"),
        exemplar_id=EXEMPLARES[i - 1].id,
        leitor_id=LEITORES[i - 1].id,
        data_checkout=now - timedelta(days=7),
        data_prevista=now + timedelta(days=7),
        data_devolucao=None,
        renovacoes=0,
        status="ativo",
    )
    for i in range(1, 3)
]

RESERVAS = [
    ReservaModel(
        id=uuid.UUID("00000000-0000-0000-0004-000000000001"),
        obra_id=OBRAS[2].id,
        leitor_id=LEITORES[2].id,
        status="aguardando",
        created_at=now,
    )
]


# ─── Runner ──────────────────────────────────────────────────────────────────

async def seed() -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        async with session.begin():
            session.add_all(OBRAS)
            session.add_all(LEITORES)
            # Exemplares dependem de obras
            session.add_all(EXEMPLARES)
            # Empréstimos dependem de exemplares e leitores
            session.add_all(EMPRESTIMOS)
            # Reservas dependem de obras e leitores
            session.add_all(RESERVAS)

    await engine.dispose()
    print("✔ Seed concluído com sucesso.")
    print(f"  {len(OBRAS)} obras, {len(EXEMPLARES)} exemplares, {len(LEITORES)} leitores,")
    print(f"  {len(EMPRESTIMOS)} empréstimos, {len(RESERVAS)} reserva(s).")


if __name__ == "__main__":
    asyncio.run(seed())
