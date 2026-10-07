from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.repositories.exemplar_repository import ExemplarRepository
from app.domain.repositories.inventario_log_repository import InventarioLogRepository


@dataclass
class ExemplarResumo:
    codigo_qr: str
    estado: str


@dataclass
class InventarioResultado:
    encontrados: list[ExemplarResumo]
    nao_bipados: list[ExemplarResumo]    # disponível na estante mas não bipado
    nao_esperados: list[ExemplarResumo]  # bipado mas localização diferente da informada


class RealizarInventarioUseCase:
    """US-019 — Realiza inventário das estantes por bipagem de QR Code.

    Recebe a lista de QR Codes bipados e a localização da estante, compara
    com o repositório de exemplares e classifica as divergências em três listas.
    Registra cada exemplar encontrado no log de auditoria.
    """

    def __init__(
        self,
        exemplar_repo: ExemplarRepository,
        inventario_log_repo: InventarioLogRepository,
    ) -> None:
        self._exemplar_repo = exemplar_repo
        self._inventario_log_repo = inventario_log_repo

    async def execute(
        self,
        codigos_qr: list[str],
        localizacao: str,
        operador_keycloak_id: str,
    ) -> InventarioResultado:
        """Executa o inventário e retorna as três listas de divergência."""
        # Resolver cada QR bipado para um exemplar (ignorando QRs desconhecidos)
        exemplares_bipados: dict[str, object] = {}
        for qr in codigos_qr:
            exemplar = await self._exemplar_repo.get_by_codigo_qr(qr)
            if exemplar is not None:
                exemplares_bipados[qr] = exemplar

        # Buscar todos os exemplares disponíveis na localização informada
        esperados = await self._exemplar_repo.list_by_localizacao(localizacao)
        esperados_qrs = {e.codigo_qr for e in esperados}

        encontrados: list[ExemplarResumo] = []
        nao_esperados: list[ExemplarResumo] = []

        for qr, exemplar in exemplares_bipados.items():
            if exemplar.localizacao_estante == localizacao:  # type: ignore[union-attr]
                encontrados.append(ExemplarResumo(codigo_qr=qr, estado=exemplar.estado))  # type: ignore[union-attr]
                await self._inventario_log_repo.registrar(
                    exemplar_id=exemplar.id,  # type: ignore[union-attr]
                    operador_keycloak_id=operador_keycloak_id,
                    acao="encontrado",
                )
            else:
                nao_esperados.append(ExemplarResumo(codigo_qr=qr, estado=exemplar.estado))  # type: ignore[union-attr]

        # Não bipados: disponíveis na estante que não apareceram na bipagem
        bipados_qrs = set(exemplares_bipados.keys())
        nao_bipados: list[ExemplarResumo] = [
            ExemplarResumo(codigo_qr=e.codigo_qr, estado=e.estado)
            for e in esperados
            if e.codigo_qr not in bipados_qrs
        ]

        return InventarioResultado(
            encontrados=encontrados,
            nao_bipados=nao_bipados,
            nao_esperados=nao_esperados,
        )
