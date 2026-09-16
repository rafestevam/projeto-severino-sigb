"""
Testes de integração — ST-02 Validação das Implementações Concretas de Repositório (US-034).
Casos cobertos: REP-001 a REP-013.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories.sqlalchemy_emprestimo_repository import SQLAlchemyEmprestimoRepository
from app.adapters.repositories.sqlalchemy_exemplar_repository import SQLAlchemyExemplarRepository
from app.adapters.repositories.sqlalchemy_leitor_repository import SQLAlchemyLeitorRepository
from app.adapters.repositories.sqlalchemy_obra_repository import SQLAlchemyObraRepository
from app.adapters.repositories.sqlalchemy_reserva_repository import SQLAlchemyReservaRepository
from app.domain.entities.emprestimo import Emprestimo
from app.domain.entities.exemplar import Exemplar
from app.domain.entities.leitor import Leitor
from app.domain.entities.obra import Obra
from app.domain.entities.reserva import Reserva

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_rep_001_obra_repository_save_and_get_by_id(db_session: AsyncSession):
    """REP-001: ObraRepository.save() persiste e get_by_id() retorna instância de Obra."""
    repo = SQLAlchemyObraRepository(db_session)
    now = datetime.now(timezone.utc)
    obra = Obra(
        id=uuid.uuid4(),
        isbn="9788535902778",
        titulo="Dom Casmurro",
        autores=["Machado de Assis"],
        editora="Ática",
        ano=1899,
        categoria="Literatura Brasileira",
        capa_url="",
        created_at=now,
    )
    saved = await repo.save(obra)
    assert isinstance(saved, Obra)
    assert saved.id == obra.id

    fetched = await repo.get_by_id(obra.id)
    assert fetched is not None
    assert isinstance(fetched, Obra)
    assert fetched.id == obra.id
    assert fetched.titulo == "Dom Casmurro"
    assert fetched.autores == ["Machado de Assis"]


async def test_rep_002_obra_repository_get_by_isbn(db_session: AsyncSession):
    """REP-002: ObraRepository.get_by_isbn() retorna a obra correta."""
    repo = SQLAlchemyObraRepository(db_session)
    isbn = f"9788525{uuid.uuid4().int % 1000000:06d}"
    now = datetime.now(timezone.utc)
    obra = Obra(
        id=uuid.uuid4(),
        isbn=isbn,
        titulo="O Cortiço",
        autores=["Aluísio Azevedo"],
        editora="Ática",
        ano=1890,
        categoria="Literatura Brasileira",
        capa_url="",
        created_at=now,
    )
    await repo.save(obra)

    fetched = await repo.get_by_isbn(isbn)
    assert fetched is not None
    assert isinstance(fetched, Obra)
    assert fetched.id == obra.id
    assert fetched.isbn == isbn


async def test_rep_003_obra_repository_list_all(db_session: AsyncSession):
    """REP-003: ObraRepository.list_all() retorna lista de Obra."""
    repo = SQLAlchemyObraRepository(db_session)
    now = datetime.now(timezone.utc)
    obra1 = Obra(
        id=uuid.uuid4(),
        isbn=f"9788500{uuid.uuid4().hex[:6]}",
        titulo="Obra List All 1",
        autores=["Autor 1"],
        editora="Editora 1",
        ano=2021,
        categoria="Categoria 1",
        capa_url="",
        created_at=now,
    )
    obra2 = Obra(
        id=uuid.uuid4(),
        isbn=f"9788500{uuid.uuid4().hex[:6]}",
        titulo="Obra List All 2",
        autores=["Autor 2"],
        editora="Editora 2",
        ano=2022,
        categoria="Categoria 2",
        capa_url="",
        created_at=now,
    )
    await repo.save(obra1)
    await repo.save(obra2)

    all_obras = await repo.list_all()
    assert isinstance(all_obras, list)
    assert all(isinstance(o, Obra) for o in all_obras)
    saved_ids = {o.id for o in all_obras}
    assert obra1.id in saved_ids
    assert obra2.id in saved_ids


async def test_rep_004_exemplar_repository_save_and_get_by_codigo_qr(db_session: AsyncSession):
    """REP-004: ExemplarRepository.save() e get_by_codigo_qr() funcionam."""
    obra_repo = SQLAlchemyObraRepository(db_session)
    exemplar_repo = SQLAlchemyExemplarRepository(db_session)
    now = datetime.now(timezone.utc)

    obra = Obra(
        id=uuid.uuid4(),
        isbn=f"9788500{uuid.uuid4().hex[:6]}",
        titulo="Obra Para Exemplar QR",
        autores=["Autor"],
        editora="Editora",
        ano=2020,
        categoria="Cat",
        capa_url="",
        created_at=now,
    )
    await obra_repo.save(obra)

    codigo_qr = f"QR-{uuid.uuid4().hex[:8]}"
    exemplar = Exemplar(
        id=uuid.uuid4(),
        obra_id=obra.id,
        codigo_qr=codigo_qr,
        estado="disponivel",
        localizacao_estante="E1",
        created_at=now,
    )
    saved = await exemplar_repo.save(exemplar)
    assert isinstance(saved, Exemplar)

    fetched = await exemplar_repo.get_by_codigo_qr(codigo_qr)
    assert fetched is not None
    assert isinstance(fetched, Exemplar)
    assert fetched.id == exemplar.id
    assert fetched.codigo_qr == codigo_qr


async def test_rep_005_exemplar_repository_list_by_obra(db_session: AsyncSession):
    """REP-005: ExemplarRepository.list_by_obra() retorna apenas exemplares da obra."""
    obra_repo = SQLAlchemyObraRepository(db_session)
    exemplar_repo = SQLAlchemyExemplarRepository(db_session)
    now = datetime.now(timezone.utc)

    obra1 = await obra_repo.save(
        Obra(
            id=uuid.uuid4(),
            isbn=f"9788500{uuid.uuid4().hex[:6]}",
            titulo="Obra 1",
            autores=["A1"],
            editora="E1",
            ano=2021,
            categoria="C1",
            capa_url="",
            created_at=now,
        )
    )
    obra2 = await obra_repo.save(
        Obra(
            id=uuid.uuid4(),
            isbn=f"9788500{uuid.uuid4().hex[:6]}",
            titulo="Obra 2",
            autores=["A2"],
            editora="E2",
            ano=2022,
            categoria="C2",
            capa_url="",
            created_at=now,
        )
    )

    exp1 = await exemplar_repo.save(
        Exemplar(
            id=uuid.uuid4(),
            obra_id=obra1.id,
            codigo_qr=f"QR-{uuid.uuid4().hex[:6]}",
            estado="disponivel",
            localizacao_estante="E1",
            created_at=now,
        )
    )
    exp2 = await exemplar_repo.save(
        Exemplar(
            id=uuid.uuid4(),
            obra_id=obra1.id,
            codigo_qr=f"QR-{uuid.uuid4().hex[:6]}",
            estado="disponivel",
            localizacao_estante="E2",
            created_at=now,
        )
    )
    exp3 = await exemplar_repo.save(
        Exemplar(
            id=uuid.uuid4(),
            obra_id=obra2.id,
            codigo_qr=f"QR-{uuid.uuid4().hex[:6]}",
            estado="disponivel",
            localizacao_estante="E3",
            created_at=now,
        )
    )

    exemplares_obra1 = await exemplar_repo.list_by_obra(obra1.id)
    assert len(exemplares_obra1) == 2
    ids_obra1 = {e.id for e in exemplares_obra1}
    assert exp1.id in ids_obra1
    assert exp2.id in ids_obra1
    assert exp3.id not in ids_obra1


async def test_rep_006_leitor_repository_save_and_get_by_cpf_hash(db_session: AsyncSession):
    """REP-006: LeitorRepository.save() e get_by_cpf_hash() funcionam."""
    repo = SQLAlchemyLeitorRepository(db_session)
    cpf = f"999888{uuid.uuid4().int % 100000:05d}"
    cpf_hash = Leitor.hash_cpf(cpf)
    now = datetime.now(timezone.utc)

    leitor = Leitor(
        id=uuid.uuid4(),
        nome="Leitor Teste Hash",
        cpf_hash=cpf_hash,
        telefone="11999990000",
        email="teste_hash@example.com",
        ativo=True,
        created_at=now,
    )
    saved = await repo.save(leitor)
    assert isinstance(saved, Leitor)

    fetched = await repo.get_by_cpf_hash(cpf_hash)
    assert fetched is not None
    assert isinstance(fetched, Leitor)
    assert fetched.id == leitor.id
    assert fetched.nome == "Leitor Teste Hash"


async def test_rep_007_leitor_repository_list_ativos(db_session: AsyncSession):
    """REP-007: LeitorRepository.list_ativos() retorna apenas leitores com ativo = True."""
    repo = SQLAlchemyLeitorRepository(db_session)
    now = datetime.now(timezone.utc)

    leitor_ativo = await repo.save(
        Leitor(
            id=uuid.uuid4(),
            nome="Ativo",
            cpf_hash=Leitor.hash_cpf(f"111{uuid.uuid4().int % 100000000:08d}"),
            telefone=None,
            email=f"ativo_{uuid.uuid4().hex[:4]}@example.com",
            ativo=True,
            created_at=now,
        )
    )
    leitor_inativo = await repo.save(
        Leitor(
            id=uuid.uuid4(),
            nome="Inativo",
            cpf_hash=Leitor.hash_cpf(f"222{uuid.uuid4().int % 100000000:08d}"),
            telefone=None,
            email=f"inativo_{uuid.uuid4().hex[:4]}@example.com",
            ativo=False,
            created_at=now,
        )
    )

    ativos = await repo.list_ativos()
    assert all(l.ativo is True for l in ativos)
    ids_ativos = {l.id for l in ativos}
    assert leitor_ativo.id in ids_ativos
    assert leitor_inativo.id not in ids_ativos


async def test_rep_008_emprestimo_repository_save_and_get_by_id(db_session: AsyncSession):
    """REP-008: EmprestimoRepository.save() e get_by_id() funcionam."""
    obra_repo = SQLAlchemyObraRepository(db_session)
    exp_repo = SQLAlchemyExemplarRepository(db_session)
    leitor_repo = SQLAlchemyLeitorRepository(db_session)
    emp_repo = SQLAlchemyEmprestimoRepository(db_session)
    now = datetime.now(timezone.utc)

    obra = await obra_repo.save(
        Obra(
            id=uuid.uuid4(),
            isbn=f"9788500{uuid.uuid4().hex[:6]}",
            titulo="Obra Emprestimo",
            autores=["Autor"],
            editora="Editora",
            ano=2021,
            categoria="Cat",
            capa_url="",
            created_at=now,
        )
    )
    exemplar = await exp_repo.save(
        Exemplar(
            id=uuid.uuid4(),
            obra_id=obra.id,
            codigo_qr=f"QR-{uuid.uuid4().hex[:6]}",
            estado="disponivel",
            localizacao_estante="E1",
            created_at=now,
        )
    )
    leitor = await leitor_repo.save(
        Leitor(
            id=uuid.uuid4(),
            nome="Leitor Emp",
            cpf_hash=Leitor.hash_cpf(f"333{uuid.uuid4().int % 100000000:08d}"),
            telefone=None,
            email=f"emp_{uuid.uuid4().hex[:4]}@example.com",
            ativo=True,
            created_at=now,
        )
    )

    emprestimo = Emprestimo(
        id=uuid.uuid4(),
        exemplar_id=exemplar.id,
        leitor_id=leitor.id,
        data_checkout=now,
        data_prevista=now + timedelta(days=14),
        data_devolucao=None,
        renovacoes=0,
        status="ativo",
    )
    saved = await emp_repo.save(emprestimo)
    assert isinstance(saved, Emprestimo)

    fetched = await emp_repo.get_by_id(emprestimo.id)
    assert fetched is not None
    assert isinstance(fetched, Emprestimo)
    assert fetched.id == emprestimo.id
    assert fetched.status == "ativo"


async def test_rep_009_emprestimo_repository_list_by_leitor(db_session: AsyncSession):
    """REP-009: EmprestimoRepository.list_by_leitor() retorna empréstimos do leitor."""
    obra_repo = SQLAlchemyObraRepository(db_session)
    exp_repo = SQLAlchemyExemplarRepository(db_session)
    leitor_repo = SQLAlchemyLeitorRepository(db_session)
    emp_repo = SQLAlchemyEmprestimoRepository(db_session)
    now = datetime.now(timezone.utc)

    obra = await obra_repo.save(
        Obra(
            id=uuid.uuid4(),
            isbn=f"9788500{uuid.uuid4().hex[:6]}",
            titulo="Obra Teste",
            autores=["Autor"],
            editora="Editora",
            ano=2021,
            categoria="Cat",
            capa_url="",
            created_at=now,
        )
    )
    exp1 = await exp_repo.save(
        Exemplar(
            id=uuid.uuid4(),
            obra_id=obra.id,
            codigo_qr=f"QR-{uuid.uuid4().hex[:6]}",
            estado="disponivel",
            localizacao_estante="E1",
            created_at=now,
        )
    )
    exp2 = await exp_repo.save(
        Exemplar(
            id=uuid.uuid4(),
            obra_id=obra.id,
            codigo_qr=f"QR-{uuid.uuid4().hex[:6]}",
            estado="disponivel",
            localizacao_estante="E2",
            created_at=now,
        )
    )
    leitor1 = await leitor_repo.save(
        Leitor(
            id=uuid.uuid4(),
            nome="L1",
            cpf_hash=Leitor.hash_cpf(f"444{uuid.uuid4().int % 100000000:08d}"),
            telefone=None,
            email=f"l1_{uuid.uuid4().hex[:4]}@example.com",
            ativo=True,
            created_at=now,
        )
    )
    leitor2 = await leitor_repo.save(
        Leitor(
            id=uuid.uuid4(),
            nome="L2",
            cpf_hash=Leitor.hash_cpf(f"555{uuid.uuid4().int % 100000000:08d}"),
            telefone=None,
            email=f"l2_{uuid.uuid4().hex[:4]}@example.com",
            ativo=True,
            created_at=now,
        )
    )

    emp1 = await emp_repo.save(
        Emprestimo(
            id=uuid.uuid4(),
            exemplar_id=exp1.id,
            leitor_id=leitor1.id,
            data_checkout=now,
            data_prevista=now + timedelta(days=14),
            data_devolucao=None,
            renovacoes=0,
            status="ativo",
        )
    )
    emp2 = await emp_repo.save(
        Emprestimo(
            id=uuid.uuid4(),
            exemplar_id=exp2.id,
            leitor_id=leitor2.id,
            data_checkout=now,
            data_prevista=now + timedelta(days=14),
            data_devolucao=None,
            renovacoes=0,
            status="ativo",
        )
    )

    l1_emps = await emp_repo.list_by_leitor(leitor1.id)
    assert len(l1_emps) == 1
    assert l1_emps[0].id == emp1.id


async def test_rep_010_emprestimo_repository_count_ativos_by_leitor(db_session: AsyncSession):
    """REP-010: EmprestimoRepository.count_ativos_by_leitor() conta corretamente."""
    obra_repo = SQLAlchemyObraRepository(db_session)
    exp_repo = SQLAlchemyExemplarRepository(db_session)
    leitor_repo = SQLAlchemyLeitorRepository(db_session)
    emp_repo = SQLAlchemyEmprestimoRepository(db_session)
    now = datetime.now(timezone.utc)

    obra = await obra_repo.save(
        Obra(
            id=uuid.uuid4(),
            isbn=f"9788500{uuid.uuid4().hex[:6]}",
            titulo="Obra Count",
            autores=["Autor"],
            editora="Editora",
            ano=2021,
            categoria="Cat",
            capa_url="",
            created_at=now,
        )
    )
    exp1 = await exp_repo.save(
        Exemplar(
            id=uuid.uuid4(),
            obra_id=obra.id,
            codigo_qr=f"QR-{uuid.uuid4().hex[:6]}",
            estado="disponivel",
            localizacao_estante="E1",
            created_at=now,
        )
    )
    exp2 = await exp_repo.save(
        Exemplar(
            id=uuid.uuid4(),
            obra_id=obra.id,
            codigo_qr=f"QR-{uuid.uuid4().hex[:6]}",
            estado="disponivel",
            localizacao_estante="E2",
            created_at=now,
        )
    )
    leitor = await leitor_repo.save(
        Leitor(
            id=uuid.uuid4(),
            nome="Leitor Multi Emprestimo",
            cpf_hash=Leitor.hash_cpf(f"666{uuid.uuid4().int % 100000000:08d}"),
            telefone=None,
            email=f"multi_{uuid.uuid4().hex[:4]}@example.com",
            ativo=True,
            created_at=now,
        )
    )

    # 1 ativo
    await emp_repo.save(
        Emprestimo(
            id=uuid.uuid4(),
            exemplar_id=exp1.id,
            leitor_id=leitor.id,
            data_checkout=now,
            data_prevista=now + timedelta(days=14),
            data_devolucao=None,
            renovacoes=0,
            status="ativo",
        )
    )
    # 1 devolvido
    await emp_repo.save(
        Emprestimo(
            id=uuid.uuid4(),
            exemplar_id=exp2.id,
            leitor_id=leitor.id,
            data_checkout=now - timedelta(days=20),
            data_prevista=now - timedelta(days=6),
            data_devolucao=now - timedelta(days=5),
            renovacoes=0,
            status="devolvido",
        )
    )

    count_ativos = await emp_repo.count_ativos_by_leitor(leitor.id)
    assert count_ativos == 1


async def test_rep_011_reserva_repository_save_and_get_by_id(db_session: AsyncSession):
    """REP-011: ReservaRepository.save() e get_by_id() funcionam."""
    obra_repo = SQLAlchemyObraRepository(db_session)
    leitor_repo = SQLAlchemyLeitorRepository(db_session)
    res_repo = SQLAlchemyReservaRepository(db_session)
    now = datetime.now(timezone.utc)

    obra = await obra_repo.save(
        Obra(
            id=uuid.uuid4(),
            isbn=f"9788500{uuid.uuid4().hex[:6]}",
            titulo="Obra Reserva",
            autores=["Autor"],
            editora="Editora",
            ano=2021,
            categoria="Cat",
            capa_url="",
            created_at=now,
        )
    )
    leitor = await leitor_repo.save(
        Leitor(
            id=uuid.uuid4(),
            nome="Leitor Reserva",
            cpf_hash=Leitor.hash_cpf(f"777{uuid.uuid4().int % 100000000:08d}"),
            telefone=None,
            email=f"res_{uuid.uuid4().hex[:4]}@example.com",
            ativo=True,
            created_at=now,
        )
    )

    reserva = Reserva(
        id=uuid.uuid4(),
        obra_id=obra.id,
        leitor_id=leitor.id,
        status="aguardando",
        created_at=now,
    )
    saved = await res_repo.save(reserva)
    assert isinstance(saved, Reserva)

    fetched = await res_repo.get_by_id(reserva.id)
    assert fetched is not None
    assert isinstance(fetched, Reserva)
    assert fetched.id == reserva.id
    assert fetched.status == "aguardando"


async def test_rep_012_reserva_repository_get_proxima_aguardando(db_session: AsyncSession):
    """REP-012: ReservaRepository.get_proxima_aguardando() retorna a reserva mais antiga no status 'aguardando'."""
    obra_repo = SQLAlchemyObraRepository(db_session)
    leitor_repo = SQLAlchemyLeitorRepository(db_session)
    res_repo = SQLAlchemyReservaRepository(db_session)
    now = datetime.now(timezone.utc)

    obra = await obra_repo.save(
        Obra(
            id=uuid.uuid4(),
            isbn=f"9788500{uuid.uuid4().hex[:6]}",
            titulo="Obra Fila Reserva",
            autores=["Autor"],
            editora="Editora",
            ano=2021,
            categoria="Cat",
            capa_url="",
            created_at=now,
        )
    )
    leitor1 = await leitor_repo.save(
        Leitor(
            id=uuid.uuid4(),
            nome="L1",
            cpf_hash=Leitor.hash_cpf(f"888{uuid.uuid4().int % 100000000:08d}"),
            telefone=None,
            email=f"rf1_{uuid.uuid4().hex[:4]}@example.com",
            ativo=True,
            created_at=now,
        )
    )
    leitor2 = await leitor_repo.save(
        Leitor(
            id=uuid.uuid4(),
            nome="L2",
            cpf_hash=Leitor.hash_cpf(f"999{uuid.uuid4().int % 100000000:08d}"),
            telefone=None,
            email=f"rf2_{uuid.uuid4().hex[:4]}@example.com",
            ativo=True,
            created_at=now,
        )
    )

    # Primeira reserva (mais antiga)
    reserva1 = await res_repo.save(
        Reserva(
            id=uuid.uuid4(),
            obra_id=obra.id,
            leitor_id=leitor1.id,
            status="aguardando",
            created_at=now - timedelta(hours=2),
        )
    )
    # Segunda reserva
    reserva2 = await res_repo.save(
        Reserva(
            id=uuid.uuid4(),
            obra_id=obra.id,
            leitor_id=leitor2.id,
            status="aguardando",
            created_at=now - timedelta(hours=1),
        )
    )

    proxima = await res_repo.get_proxima_aguardando(obra.id)
    assert proxima is not None
    assert proxima.id == reserva1.id


async def test_rep_013_returned_objects_are_domain_entities_not_orm(db_session: AsyncSession):
    """REP-013: Objetos retornados pelos repositórios são entidades de domínio, não modelos ORM."""
    obra_repo = SQLAlchemyObraRepository(db_session)
    exp_repo = SQLAlchemyExemplarRepository(db_session)
    leitor_repo = SQLAlchemyLeitorRepository(db_session)
    emp_repo = SQLAlchemyEmprestimoRepository(db_session)
    res_repo = SQLAlchemyReservaRepository(db_session)
    now = datetime.now(timezone.utc)

    obra = await obra_repo.save(
        Obra(
            id=uuid.uuid4(),
            isbn=f"9788500{uuid.uuid4().hex[:6]}",
            titulo="Obra Entidade",
            autores=["Autor"],
            editora="Editora",
            ano=2021,
            categoria="Cat",
            capa_url="",
            created_at=now,
        )
    )
    exp = await exp_repo.save(
        Exemplar(
            id=uuid.uuid4(),
            obra_id=obra.id,
            codigo_qr=f"QR-{uuid.uuid4().hex[:6]}",
            estado="disponivel",
            localizacao_estante="E1",
            created_at=now,
        )
    )
    leitor = await leitor_repo.save(
        Leitor(
            id=uuid.uuid4(),
            nome="Leitor",
            cpf_hash=Leitor.hash_cpf(f"101{uuid.uuid4().int % 100000000:08d}"),
            telefone=None,
            email=f"ent_{uuid.uuid4().hex[:4]}@example.com",
            ativo=True,
            created_at=now,
        )
    )
    emp = await emp_repo.save(
        Emprestimo(
            id=uuid.uuid4(),
            exemplar_id=exp.id,
            leitor_id=leitor.id,
            data_checkout=now,
            data_prevista=now + timedelta(days=14),
            data_devolucao=None,
            renovacoes=0,
            status="ativo",
        )
    )
    res = await res_repo.save(
        Reserva(
            id=uuid.uuid4(),
            obra_id=obra.id,
            leitor_id=leitor.id,
            status="aguardando",
            created_at=now,
        )
    )

    f_obra = await obra_repo.get_by_id(obra.id)
    f_exp = await exp_repo.get_by_id(exp.id)
    f_leitor = await leitor_repo.get_by_id(leitor.id)
    f_emp = await emp_repo.get_by_id(emp.id)
    f_res = await res_repo.get_by_id(res.id)

    assert type(f_obra) is Obra
    assert type(f_exp) is Exemplar
    assert type(f_leitor) is Leitor
    assert type(f_emp) is Emprestimo
    assert type(f_res) is Reserva
