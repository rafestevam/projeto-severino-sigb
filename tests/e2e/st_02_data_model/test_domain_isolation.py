"""
Testes de análise estática — ST-02 Isolamento da Camada de Domínio (US-034).
Casos cobertos: DOM-001 a DOM-006.
"""

from __future__ import annotations

import inspect
from abc import ABC
from pathlib import Path

import pytest

pytestmark = [pytest.mark.static]

DOMAIN_DIR = Path(__file__).parents[3] / "app" / "domain"
ENTITIES_DIR = DOMAIN_DIR / "entities"
REPOSITORIES_DIR = DOMAIN_DIR / "repositories"


def _get_all_domain_py_files() -> list[Path]:
    """Retorna todos os arquivos .py no diretório app/domain recursivamente."""
    return [p for p in DOMAIN_DIR.rglob("*.py") if p.is_file()]


def test_dom_001_no_sqlalchemy_imports():
    """DOM-001: Nenhum arquivo em app/domain/ importa sqlalchemy."""
    py_files = _get_all_domain_py_files()
    assert len(py_files) > 0, "Nenhum arquivo Python encontrado em app/domain/"

    violations = []
    for file_path in py_files:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "import sqlalchemy" in stripped or "from sqlalchemy" in stripped:
                violations.append(f"{file_path.relative_to(DOMAIN_DIR.parent.parent)}:{idx}: {stripped}")

    assert not violations, f"Violações de importação do SQLAlchemy encontradas no domínio:\n" + "\n".join(violations)


def test_dom_002_no_fastapi_imports():
    """DOM-002: Nenhum arquivo em app/domain/ importa fastapi."""
    py_files = _get_all_domain_py_files()
    assert len(py_files) > 0, "Nenhum arquivo Python encontrado em app/domain/"

    violations = []
    for file_path in py_files:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "import fastapi" in stripped or "from fastapi" in stripped:
                violations.append(f"{file_path.relative_to(DOMAIN_DIR.parent.parent)}:{idx}: {stripped}")

    assert not violations, f"Violações de importação do FastAPI encontradas no domínio:\n" + "\n".join(violations)


def test_dom_003_no_httpx_imports():
    """DOM-003: Nenhum arquivo em app/domain/ importa httpx."""
    py_files = _get_all_domain_py_files()
    assert len(py_files) > 0, "Nenhum arquivo Python encontrado em app/domain/"

    violations = []
    for file_path in py_files:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "import httpx" in stripped or "from httpx" in stripped:
                violations.append(f"{file_path.relative_to(DOMAIN_DIR.parent.parent)}:{idx}: {stripped}")

    assert not violations, f"Violações de importação do HTTPX encontradas no domínio:\n" + "\n".join(violations)


def test_dom_004_entities_exist():
    """DOM-004: Os 5 arquivos de entidade existem em app/domain/entities/."""
    expected_entities = ["obra.py", "exemplar.py", "leitor.py", "emprestimo.py", "reserva.py"]
    for entity_file in expected_entities:
        target = ENTITIES_DIR / entity_file
        assert target.exists() and target.is_file(), f"Arquivo de entidade ausente: {entity_file}"


def test_dom_005_repositories_exist():
    """DOM-005: Os 5 arquivos de ABC de repositório existem em app/domain/repositories/."""
    expected_repos = [
        "obra_repository.py",
        "exemplar_repository.py",
        "leitor_repository.py",
        "emprestimo_repository.py",
        "reserva_repository.py",
    ]
    for repo_file in expected_repos:
        target = REPOSITORIES_DIR / repo_file
        assert target.exists() and target.is_file(), f"Arquivo de repositório ausente: {repo_file}"


def test_dom_006_repository_abcs_valid():
    """DOM-006: Cada ABC de repositório herda de ABC e possui pelo menos um abstractmethod."""
    from app.domain.repositories.emprestimo_repository import EmprestimoRepository
    from app.domain.repositories.exemplar_repository import ExemplarRepository
    from app.domain.repositories.leitor_repository import LeitorRepository
    from app.domain.repositories.obra_repository import ObraRepository
    from app.domain.repositories.reserva_repository import ReservaRepository

    repo_classes = [
        ObraRepository,
        ExemplarRepository,
        LeitorRepository,
        EmprestimoRepository,
        ReservaRepository,
    ]

    for repo_cls in repo_classes:
        assert issubclass(repo_cls, ABC), f"{repo_cls.__name__} não herda de ABC"
        abstract_methods = getattr(repo_cls, "__abstractmethods__", set())
        assert len(abstract_methods) > 0, f"{repo_cls.__name__} não possui métodos abstratos definidos"
