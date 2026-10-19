from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.domain.entities.leitor import Leitor
from app.domain.exceptions import LeitorJaCadastradoError
from app.domain.repositories.leitor_repository import LeitorRepository
from app.domain.value_objects.cpf import Cpf


@dataclass(frozen=True, slots=True)
class DadosPreCadastro:
    nome: str
    cpf: str
    telefone: str | None = None
    email: str | None = None


def _texto_opcional(valor: str | None) -> str | None:
    if valor is None:
        return None
    return valor.strip() or None


class PreCadastrarLeitorUseCase:
    """US-030 — Pré-cadastro público de leitor, que nasce pendente (ativo=False)."""

    def __init__(self, leitor_repo: LeitorRepository) -> None:
        self._leitor_repo = leitor_repo

    async def execute(self, dados: DadosPreCadastro) -> Leitor:
        """
        Raises:
            CpfInvalidoError: se o CPF não passa na validação de dígitos.
            LeitorJaCadastradoError: se já existe leitor com o mesmo CPF.
        """
        cpf_hash = Cpf.de(dados.cpf).hash()
        if await self._leitor_repo.get_by_cpf_hash(cpf_hash) is not None:
            raise LeitorJaCadastradoError()

        email = _texto_opcional(dados.email)
        leitor = Leitor(
            id=uuid4(),
            nome=dados.nome.strip(),
            cpf_hash=cpf_hash,
            telefone=_texto_opcional(dados.telefone),
            email=email.lower() if email else None,
            ativo=False,
            created_at=datetime.now(timezone.utc),
        )
        return await self._leitor_repo.save(leitor)
