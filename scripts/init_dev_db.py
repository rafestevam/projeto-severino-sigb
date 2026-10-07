"""
Seed mínimo para o deploy temporário de desenvolvimento.

Insere obras, exemplares, leitores e 1 empréstimo ativo usando o
DATABASE_URL do ambiente (PostgreSQL local).

Uso:
  DATABASE_URL=postgresql+asyncpg://libsys:changeme@localhost:5432/libsysdb \\
    DEV_MODE=1 python scripts/init_dev_db.py
"""
from __future__ import annotations

import asyncio
import hashlib
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Garante que o pacote 'app' seja encontrado quando executado da raiz
sys.path.insert(0, str(Path(__file__).parent.parent))

# DATABASE_URL deve estar no ambiente antes de importar o módulo database
from app.infrastructure.database import _get_engine, _get_session_local  # noqa: E402
import app.adapters.repositories.models  # noqa: F401, E402 — popula Base.metadata
from app.infrastructure.database import Base  # noqa: E402
from app.adapters.repositories.models.obra import ObraModel
from app.adapters.repositories.models.exemplar import ExemplarModel
from app.adapters.repositories.models.leitor import LeitorModel
from app.adapters.repositories.models.emprestimo import EmprestimoModel

from sqlalchemy.ext.asyncio import AsyncSession


async def seed() -> None:
    now = datetime.now(timezone.utc)
    due = now + timedelta(days=14)

    cpf1 = "12345678901"
    cpf2 = "98765432100"

    obras = [
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
            total_emprestimos=3,
        ),
        ObraModel(
            id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            isbn="9788525432124",
            titulo="O Senhor dos Anéis",
            autores=["J.R.R. Tolkien"],
            editora="HarperCollins",
            ano=1954,
            capa_url=None,
            categoria="Fantasia",
            created_at=now,
            total_emprestimos=7,
        ),
        ObraModel(
            id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
            isbn="9788560088539",
            titulo="Introdução à Computação",
            autores=["Ada Lovelace", "Charles Babbage"],
            editora="TechBooks",
            ano=2020,
            capa_url=None,
            categoria="Ciência da Computação",
            created_at=now,
            total_emprestimos=1,
        ),
    ]

    exemplares = [
        ExemplarModel(
            id=uuid.UUID("00000000-0000-0000-0001-000000000001"),
            obra_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            codigo_qr="LIB-2025-00001",
            estado="disponivel",
            localizacao_estante="A-01",
            created_at=now,
            origem="compra",
        ),
        ExemplarModel(
            id=uuid.UUID("00000000-0000-0000-0001-000000000002"),
            obra_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            codigo_qr="LIB-2025-00002",
            estado="emprestado",
            localizacao_estante="A-01",
            created_at=now,
            origem="compra",
        ),
        ExemplarModel(
            id=uuid.UUID("00000000-0000-0000-0001-000000000003"),
            obra_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            codigo_qr="LIB-2025-00003",
            estado="disponivel",
            localizacao_estante="B-02",
            created_at=now,
            origem="doacao",
        ),
        ExemplarModel(
            id=uuid.UUID("00000000-0000-0000-0001-000000000004"),
            obra_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
            codigo_qr="LIB-2025-00004",
            estado="disponivel",
            localizacao_estante="C-03",
            created_at=now,
            origem="compra",
        ),
    ]

    leitores = [
        LeitorModel(
            id=uuid.UUID("00000000-0000-0000-0002-000000000001"),
            nome="João da Silva",
            cpf_hash=hashlib.sha256(cpf1.encode()).hexdigest(),
            telefone="11999990001",
            email="joao@example.com",
            ativo=True,
            created_at=now,
        ),
        LeitorModel(
            id=uuid.UUID("00000000-0000-0000-0002-000000000002"),
            nome="Maria Oliveira",
            cpf_hash=hashlib.sha256(cpf2.encode()).hexdigest(),
            telefone="11999990002",
            email="maria@example.com",
            ativo=True,
            created_at=now,
        ),
    ]

    emprestimos = [
        EmprestimoModel(
            id=uuid.UUID("00000000-0000-0000-0003-000000000001"),
            exemplar_id=uuid.UUID("00000000-0000-0000-0001-000000000002"),
            leitor_id=uuid.UUID("00000000-0000-0000-0002-000000000001"),
            data_checkout=now,
            data_prevista=due,
            data_devolucao=None,
            renovacoes=0,
            status="ativo",
        ),
    ]

    session_factory = _get_session_local()
    async with session_factory() as session:
        session.add_all(obras)
        await session.flush()
        session.add_all(exemplares)
        session.add_all(leitores)
        await session.flush()
        session.add_all(emprestimos)
        await session.commit()

    print("✓ Seed inserido com sucesso")
    print()
    print("  Leitores para teste:")
    print(f"    CPF {cpf1}  →  João da Silva")
    print(f"    CPF {cpf2}  →  Maria Oliveira")
    print()
    print("  Exemplares disponíveis:")
    print("    QR: LIB-2025-00001  →  Dom Casmurro (disponivel)")
    print("    QR: LIB-2025-00002  →  Dom Casmurro (EMPRESTADO para João)")
    print("    QR: LIB-2025-00003  →  O Senhor dos Anéis (disponivel)")
    print("    QR: LIB-2025-00004  →  Introdução à Computação (disponivel)")


async def main() -> None:
    await seed()
    await _get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main())
