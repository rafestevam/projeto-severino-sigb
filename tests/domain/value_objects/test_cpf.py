"""Testes unitários para o value object Cpf (US-030)."""
from __future__ import annotations

import hashlib

import pytest

from app.domain.exceptions import CpfInvalidoError
from app.domain.value_objects.cpf import Cpf, hash_cpf, normalizar_cpf

_CPF_VALIDO = "52998224725"
_CPF_VALIDO_MASCARADO = "529.982.247-25"


class TestCpfDe:
    def test_aceita_cpf_valido_sem_mascara(self) -> None:
        assert Cpf.de(_CPF_VALIDO).digitos == _CPF_VALIDO

    def test_aceita_cpf_valido_com_mascara(self) -> None:
        assert Cpf.de(_CPF_VALIDO_MASCARADO).digitos == _CPF_VALIDO

    @pytest.mark.parametrize("cpf", ["111.444.777-35", "39053344705", "00000000191"])
    def test_aceita_outros_cpfs_validos(self, cpf: str) -> None:
        Cpf.de(cpf)

    @pytest.mark.parametrize("cpf", ["529.982.247-24", "52998224715", "12345678900"])
    def test_rejeita_digitos_verificadores_errados(self, cpf: str) -> None:
        with pytest.raises(CpfInvalidoError):
            Cpf.de(cpf)

    @pytest.mark.parametrize("cpf", ["000.000.000-00", "11111111111", "99999999999"])
    def test_rejeita_sequencias_repetidas(self, cpf: str) -> None:
        with pytest.raises(CpfInvalidoError):
            Cpf.de(cpf)

    @pytest.mark.parametrize("cpf", ["", "123", "5299822472", "529982247250", "abc.def.ghi-jk"])
    def test_rejeita_tamanho_diferente_de_11_digitos(self, cpf: str) -> None:
        with pytest.raises(CpfInvalidoError):
            Cpf.de(cpf)

    def test_mensagem_de_erro_nao_contem_o_cpf(self) -> None:
        with pytest.raises(CpfInvalidoError) as exc_info:
            Cpf.de("529.982.247-24")
        assert "529" not in str(exc_info.value)

    def test_e_imutavel(self) -> None:
        cpf = Cpf.de(_CPF_VALIDO)
        with pytest.raises(AttributeError):
            cpf.digitos = "00000000000"  # type: ignore[misc]


class TestCpfHash:
    def test_hash_e_sha256_dos_digitos(self) -> None:
        esperado = hashlib.sha256(_CPF_VALIDO.encode()).hexdigest()
        assert Cpf.de(_CPF_VALIDO_MASCARADO).hash() == esperado

    def test_hash_com_e_sem_mascara_coincidem(self) -> None:
        assert Cpf.de(_CPF_VALIDO).hash() == Cpf.de(_CPF_VALIDO_MASCARADO).hash()


class TestFuncoesAuxiliares:
    def test_normalizar_remove_pontuacao_e_espacos(self) -> None:
        assert normalizar_cpf(" 529.982.247-25 ") == _CPF_VALIDO

    def test_hash_cpf_nao_valida_digitos(self) -> None:
        """CPFs legados (seed) com dígitos inválidos continuam com o mesmo hash."""
        assert hash_cpf("12345678900") == hashlib.sha256(b"12345678900").hexdigest()
