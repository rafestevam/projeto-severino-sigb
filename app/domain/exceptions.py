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
