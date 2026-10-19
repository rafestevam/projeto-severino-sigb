"""Testes unitários para os schemas do OPAC (ST-08): leitor, obra pública e reserva."""
from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.adapters.api.schemas.leitor import LeitorOut, LeitorPreCadastroIn, LeitorPreCadastroOut
from app.adapters.api.schemas.obra import (
    ObraIn,
    ObraPublicaDetalheOut,
    ObraPublicaListOut,
    ObraPublicaOut,
)
from app.adapters.api.schemas.reserva import ReservaMinhaIn
from app.domain.entities.disponibilidade_obra import DisponibilidadeObra
from app.use_cases.listar_catalogo_publico import ItemCatalogo, PaginaCatalogo
from app.use_cases.obter_obra_publica import DetalheObraPublica
from tests.domain.repositories.conftest import make_leitor, make_obra

_CAMPOS_SENSIVEIS = {"cpf_hash", "telefone", "email", "leitor_id", "isbn", "created_at"}


class TestLeitorOut:
    def test_status_ativo(self) -> None:
        assert LeitorOut.model_validate(make_leitor(ativo=True)).status == "ativo"

    def test_status_pendente(self) -> None:
        dados = LeitorOut.model_validate(make_leitor(ativo=False)).model_dump()
        assert dados["status"] == "pendente"
        assert "cpf_hash" not in dados


class TestLeitorPreCadastroIn:
    def test_contatos_opcionais(self) -> None:
        body = LeitorPreCadastroIn(nome="Ana Lima", cpf="52998224725")
        assert body.telefone is None and body.email is None

    def test_strings_vazias_viram_none(self) -> None:
        body = LeitorPreCadastroIn(nome="Ana Lima", cpf="52998224725", telefone=" ", email="")
        assert body.telefone is None and body.email is None

    def test_rejeita_email_malformado(self) -> None:
        with pytest.raises(ValidationError):
            LeitorPreCadastroIn(nome="Ana Lima", cpf="52998224725", email="nao-e-email")

    def test_rejeita_nome_curto(self) -> None:
        with pytest.raises(ValidationError):
            LeitorPreCadastroIn(nome="A", cpf="52998224725")

    def test_aceita_cpf_mascarado(self) -> None:
        assert LeitorPreCadastroIn(nome="Ana", cpf="529.982.247-25").cpf == "529.982.247-25"


class TestLeitorPreCadastroOut:
    def test_expoe_apenas_status(self) -> None:
        assert LeitorPreCadastroOut().model_dump() == {"status": "pendente"}


class TestObraPublica:
    def test_card_sem_campos_sensiveis(self) -> None:
        obra = make_obra(id=uuid4())
        item = ItemCatalogo(obra, DisponibilidadeObra(obra.id, 1, 0))

        dados = ObraPublicaOut.de_item(item).model_dump()

        assert dados["disponivel"] is True
        assert not _CAMPOS_SENSIVEIS & dados.keys()

    def test_lista_preserva_paginacao(self) -> None:
        obra = make_obra(id=uuid4())
        pagina = PaginaCatalogo([ItemCatalogo(obra, DisponibilidadeObra(obra.id, 0, 1))], 31, 2, 10)

        out = ObraPublicaListOut.de_pagina(pagina)

        assert (out.total, out.page, out.page_size) == (31, 2, 10)
        assert out.items[0].disponivel is False

    def test_detalhe_traz_contagens_e_ranking(self) -> None:
        obra = make_obra(id=uuid4())
        obra.sinopse = "Uma história."
        detalhe = DetalheObraPublica(obra, DisponibilidadeObra(obra.id, 2, 3), posicao_ranking=4)

        dados = ObraPublicaDetalheOut.de_detalhe(detalhe).model_dump()

        assert dados["exemplares_disponiveis"] == 2
        assert dados["exemplares_emprestados"] == 3
        assert dados["posicao_ranking"] == 4
        assert dados["sinopse"] == "Uma história."
        assert not _CAMPOS_SENSIVEIS & dados.keys()


class TestObraInSinopse:
    def test_sinopse_opcional(self) -> None:
        body = ObraIn(titulo="T", autores=["A"], editora="E", ano=2000, categoria="C")
        assert body.sinopse is None


class TestReservaMinhaIn:
    def test_ignora_leitor_id_enviado_pelo_cliente(self) -> None:
        body = ReservaMinhaIn.model_validate({"obra_id": str(uuid4()), "leitor_id": str(uuid4())})
        assert "leitor_id" not in body.model_dump()
