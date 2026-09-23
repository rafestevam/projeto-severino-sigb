"""
Testes unitários para as exceções de domínio em app/domain/exceptions.py.

Cobre:
  - DuplicateIsbnError: herança, mensagem, atributo isbn.
  - ObraNotFoundError: herança, mensagem, atributo identifier.
  - ExemplarNotFoundError: herança, mensagem, atributo identifier.
  - ExemplarNaoDisponivelError: herança, mensagem, atributos exemplar_id e estado_atual.
  - LeitorInativoError: herança, mensagem, atributo leitor_id.
  - LimiteEmprestimosAtingidoError: herança, mensagem, atributos leitor_id e limite.
  - EmprestimoNaoEncontradoError: herança, mensagem, atributo identifier.
  - LimiteRenovacoesAtingidoError: herança, mensagem, atributos emprestimo_id e limite.
  - EmprestimoSemAtivoPorQrError: herança, mensagem, atributo codigo_qr.
"""
from __future__ import annotations

import pytest

from app.domain.exceptions import (
    DuplicateIsbnError,
    EmprestimoNaoEncontradoError,
    EmprestimoSemAtivoPorQrError,
    ExemplarNaoDisponivelError,
    ExemplarNotFoundError,
    LeitorInativoError,
    LimiteEmprestimosAtingidoError,
    LimiteRenovacoesAtingidoError,
    ObraNotFoundError,
)


# ---------------------------------------------------------------------------
# DuplicateIsbnError
# ---------------------------------------------------------------------------


class TestDuplicateIsbnError:
    def test_e_subclasse_de_value_error(self):
        """DuplicateIsbnError deve herdar de ValueError."""
        assert issubclass(DuplicateIsbnError, ValueError)

    def test_pode_ser_levantada(self):
        """DuplicateIsbnError deve poder ser levantada e capturada."""
        with pytest.raises(DuplicateIsbnError):
            raise DuplicateIsbnError("9788535902778")

    def test_capturada_como_value_error(self):
        """Por herança, deve ser capturável como ValueError."""
        with pytest.raises(ValueError):
            raise DuplicateIsbnError("9788535902778")

    def test_atributo_isbn_armazenado(self):
        """O atributo isbn deve conter o ISBN passado no construtor."""
        exc = DuplicateIsbnError("9788535902778")
        assert exc.isbn == "9788535902778"

    def test_mensagem_contem_isbn(self):
        """A mensagem de erro deve mencionar o ISBN."""
        exc = DuplicateIsbnError("9788535902778")
        assert "9788535902778" in str(exc)

    def test_isbn_diferente(self):
        """O atributo isbn deve refletir o ISBN passado, independente do valor."""
        exc = DuplicateIsbnError("0000000000000")
        assert exc.isbn == "0000000000000"

    def test_instancias_distintas_para_isbns_distintos(self):
        """Duas instâncias com ISBNs distintos devem ter atributo isbn distinto."""
        exc_a = DuplicateIsbnError("9788535902778")
        exc_b = DuplicateIsbnError("9780132350884")
        assert exc_a.isbn != exc_b.isbn


# ---------------------------------------------------------------------------
# ObraNotFoundError
# ---------------------------------------------------------------------------


class TestObraNotFoundError:
    def test_e_subclasse_de_value_error(self):
        """ObraNotFoundError deve herdar de ValueError."""
        assert issubclass(ObraNotFoundError, ValueError)

    def test_pode_ser_levantada(self):
        """ObraNotFoundError deve poder ser levantada e capturada."""
        with pytest.raises(ObraNotFoundError):
            raise ObraNotFoundError("some-uuid")

    def test_capturada_como_value_error(self):
        """Por herança, deve ser capturável como ValueError."""
        with pytest.raises(ValueError):
            raise ObraNotFoundError("some-uuid")

    def test_atributo_identifier_armazenado(self):
        """O atributo identifier deve conter o valor passado no construtor."""
        exc = ObraNotFoundError("abc-123")
        assert exc.identifier == "abc-123"

    def test_mensagem_contem_identifier(self):
        """A mensagem de erro deve mencionar o identifier."""
        exc = ObraNotFoundError("abc-123")
        assert "abc-123" in str(exc)

    def test_identifier_uuid_string(self):
        """Deve aceitar um UUID em formato de string como identifier."""
        uid = "00000000-0000-0000-0000-000000000099"
        exc = ObraNotFoundError(uid)
        assert exc.identifier == uid


# ---------------------------------------------------------------------------
# ExemplarNotFoundError
# ---------------------------------------------------------------------------


class TestExemplarNotFoundError:
    def test_e_subclasse_de_value_error(self):
        """ExemplarNotFoundError deve herdar de ValueError."""
        assert issubclass(ExemplarNotFoundError, ValueError)

    def test_pode_ser_levantada(self):
        """ExemplarNotFoundError deve poder ser levantada e capturada."""
        with pytest.raises(ExemplarNotFoundError):
            raise ExemplarNotFoundError("LIB-2025-00001")

    def test_capturada_como_value_error(self):
        """Por herança, deve ser capturável como ValueError."""
        with pytest.raises(ValueError):
            raise ExemplarNotFoundError("LIB-2025-00001")

    def test_atributo_identifier_armazenado(self):
        """O atributo identifier deve conter o código QR passado no construtor."""
        exc = ExemplarNotFoundError("LIB-2025-00007")
        assert exc.identifier == "LIB-2025-00007"

    def test_mensagem_contem_identifier(self):
        """A mensagem de erro deve mencionar o identifier."""
        exc = ExemplarNotFoundError("LIB-2025-00007")
        assert "LIB-2025-00007" in str(exc)

    def test_identifier_qualquer_string(self):
        """Deve aceitar qualquer string como identifier."""
        exc = ExemplarNotFoundError("codigo-arbitrario-xyz")
        assert exc.identifier == "codigo-arbitrario-xyz"


# ---------------------------------------------------------------------------
# ExemplarNaoDisponivelError
# ---------------------------------------------------------------------------


class TestExemplarNaoDisponivelError:
    def test_e_subclasse_de_value_error(self):
        assert issubclass(ExemplarNaoDisponivelError, ValueError)

    def test_atributos_armazenados(self):
        exc = ExemplarNaoDisponivelError("ex-123", "emprestado")
        assert exc.exemplar_id == "ex-123"
        assert exc.estado_atual == "emprestado"
        assert "ex-123" in str(exc)
        assert "emprestado" in str(exc)


# ---------------------------------------------------------------------------
# LeitorInativoError
# ---------------------------------------------------------------------------


class TestLeitorInativoError:
    def test_e_subclasse_de_value_error(self):
        assert issubclass(LeitorInativoError, ValueError)

    def test_atributos_armazenados(self):
        exc = LeitorInativoError("leitor-123")
        assert exc.leitor_id == "leitor-123"
        assert "leitor-123" in str(exc)


# ---------------------------------------------------------------------------
# LimiteEmprestimosAtingidoError
# ---------------------------------------------------------------------------


class TestLimiteEmprestimosAtingidoError:
    def test_e_subclasse_de_value_error(self):
        assert issubclass(LimiteEmprestimosAtingidoError, ValueError)

    def test_atributos_armazenados(self):
        exc = LimiteEmprestimosAtingidoError("leitor-123", 3)
        assert exc.leitor_id == "leitor-123"
        assert exc.limite == 3
        assert "leitor-123" in str(exc)
        assert "3" in str(exc)


# ---------------------------------------------------------------------------
# EmprestimoNaoEncontradoError
# ---------------------------------------------------------------------------


class TestEmprestimoNaoEncontradoError:
    def test_e_subclasse_de_value_error(self):
        assert issubclass(EmprestimoNaoEncontradoError, ValueError)

    def test_atributos_armazenados(self):
        exc = EmprestimoNaoEncontradoError("emp-123")
        assert exc.identifier == "emp-123"
        assert "emp-123" in str(exc)


# ---------------------------------------------------------------------------
# LimiteRenovacoesAtingidoError
# ---------------------------------------------------------------------------


class TestLimiteRenovacoesAtingidoError:
    def test_e_subclasse_de_value_error(self):
        assert issubclass(LimiteRenovacoesAtingidoError, ValueError)

    def test_atributos_armazenados(self):
        exc = LimiteRenovacoesAtingidoError("emp-123", 3)
        assert exc.emprestimo_id == "emp-123"
        assert exc.limite == 3
        assert "emp-123" in str(exc)
        assert "3" in str(exc)


# ---------------------------------------------------------------------------
# EmprestimoSemAtivoPorQrError
# ---------------------------------------------------------------------------


class TestEmprestimoSemAtivoPorQrError:
    def test_e_subclasse_de_value_error(self):
        assert issubclass(EmprestimoSemAtivoPorQrError, ValueError)

    def test_atributos_armazenados(self):
        exc = EmprestimoSemAtivoPorQrError("QR-999")
        assert exc.codigo_qr == "QR-999"
        assert "QR-999" in str(exc)


# ---------------------------------------------------------------------------
# Isolamento entre as exceções
# ---------------------------------------------------------------------------


class TestIsolamentoExcecoes:
    def test_duplicate_isbn_nao_e_obra_not_found(self):
        """DuplicateIsbnError e ObraNotFoundError são tipos distintos."""
        assert not issubclass(DuplicateIsbnError, ObraNotFoundError)
        assert not issubclass(ObraNotFoundError, DuplicateIsbnError)

    def test_duplicate_isbn_nao_e_exemplar_not_found(self):
        """DuplicateIsbnError e ExemplarNotFoundError são tipos distintos."""
        assert not issubclass(DuplicateIsbnError, ExemplarNotFoundError)

    def test_obra_not_found_nao_captura_exemplar_not_found(self):
        """Capturar ObraNotFoundError não deve capturar ExemplarNotFoundError."""
        with pytest.raises(ExemplarNotFoundError):
            try:
                raise ExemplarNotFoundError("LIB-2025-00001")
            except ObraNotFoundError:
                pass  # não deve entrar aqui
