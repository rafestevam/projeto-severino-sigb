from __future__ import annotations


class DuplicateIsbnError(ValueError):
    """Raised when an obra with the same ISBN already exists in the repository."""

    def __init__(self, isbn: str) -> None:
        super().__init__(f"ISBN já cadastrado: {isbn}")
        self.isbn = isbn


class ObraNotFoundError(ValueError):
    """Raised when an obra cannot be found by the given identifier."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Obra não encontrada: {identifier}")
        self.identifier = identifier


class ExemplarNotFoundError(ValueError):
    """Raised when an exemplar cannot be found by the given identifier."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Exemplar não encontrado: {identifier}")
        self.identifier = identifier


class ExemplarNaoDisponivelError(ValueError):
    """Raised when an exemplar is not in available state for checkout."""

    def __init__(self, exemplar_id: str, estado_atual: str = "") -> None:
        msg = f"Exemplar não disponível para empréstimo: {exemplar_id}"
        if estado_atual:
            msg += f" (estado atual: {estado_atual})"
        super().__init__(msg)
        self.exemplar_id = exemplar_id
        self.estado_atual = estado_atual


class LeitorInativoError(ValueError):
    """Raised when an operation requires an active reader but the reader is inactive."""

    def __init__(self, leitor_id: str) -> None:
        super().__init__(f"Leitor inativo: {leitor_id}")
        self.leitor_id = leitor_id


class LimiteEmprestimosAtingidoError(ValueError):
    """Raised when a reader has reached the maximum allowed active loans."""

    def __init__(self, leitor_id: str, limite: int) -> None:
        super().__init__(
            f"Limite de empréstimos atingido para o leitor {leitor_id} (limite: {limite})"
        )
        self.leitor_id = leitor_id
        self.limite = limite


class EmprestimoNaoEncontradoError(ValueError):
    """Raised when a loan cannot be found by the given identifier."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Empréstimo não encontrado: {identifier}")
        self.identifier = identifier


class LimiteRenovacoesAtingidoError(ValueError):
    """Raised when a loan has reached the maximum number of renewals allowed."""

    def __init__(self, emprestimo_id: str, limite: int) -> None:
        super().__init__(
            f"Limite de renovações atingido para o empréstimo {emprestimo_id} (limite: {limite})"
        )
        self.emprestimo_id = emprestimo_id
        self.limite = limite


class EmprestimoSemAtivoPorQrError(ValueError):
    """Raised when no active loan exists for the given exemplar QR code."""

    def __init__(self, codigo_qr: str) -> None:
        super().__init__(f"Nenhum empréstimo ativo encontrado para o QR Code: {codigo_qr}")
        self.codigo_qr = codigo_qr


class ReservaNaoEncontradaError(ValueError):
    """Raised when a reservation cannot be found by the given identifier."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Reserva não encontrada: {identifier}")
        self.identifier = identifier


class ReservaJaExisteError(ValueError):
    """Raised when the reader already has an active reservation for the same work."""

    def __init__(self, obra_id: str, leitor_id: str) -> None:
        super().__init__(
            f"Leitor {leitor_id} já possui reserva ativa para a obra {obra_id}"
        )
        self.obra_id = obra_id
        self.leitor_id = leitor_id


class ObraComExemplarDisponivelError(ValueError):
    """Raised when trying to reserve a work that has available copies (no need to reserve)."""

    def __init__(self, obra_id: str) -> None:
        super().__init__(
            f"A obra {obra_id} possui exemplar disponível — realize o empréstimo diretamente"
        )
        self.obra_id = obra_id
