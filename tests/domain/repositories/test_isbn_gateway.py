"""
Testes unitários para IsbnGateway (ABC).

Estratégia: implementar um stub in-memory concreto da ABC para
verificar que o contrato é respeitado sem nenhuma dependência de rede.
O stub retorna dados controlados; os testes garantem que a ABC é
respeitada e que implementações concretas produzem o tipo correto.
"""
from __future__ import annotations

import pytest

from app.adapters.api.schemas.isbn_metadata import IsbnMetadataOut
from app.domain.gateways.isbn_gateway import IsbnGateway


# ---------------------------------------------------------------------------
# Stub in-memory — implementação concreta mínima da ABC
# ---------------------------------------------------------------------------

class InMemoryIsbnGateway(IsbnGateway):
    """Gateway de teste que retorna dados de um dicionário em memória."""

    def __init__(self, data: dict[str, IsbnMetadataOut] | None = None) -> None:
        self._data: dict[str, IsbnMetadataOut] = data or {}

    async def buscar(self, isbn: str) -> IsbnMetadataOut | None:
        return self._data.get(isbn)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def gateway_vazio() -> InMemoryIsbnGateway:
    return InMemoryIsbnGateway()


@pytest.fixture
def gateway_com_dados() -> InMemoryIsbnGateway:
    return InMemoryIsbnGateway(
        data={
            "9788535902778": IsbnMetadataOut(
                titulo="Dom Casmurro",
                autores=["Machado de Assis"],
                editora="Ática",
                ano=1899,
                capa_url="https://example.com/capa.jpg",
            ),
            "9780132350884": IsbnMetadataOut(
                titulo="Clean Code",
                autores=["Robert C. Martin"],
                editora="Prentice Hall",
                ano=2008,
                capa_url=None,
            ),
        }
    )


# ---------------------------------------------------------------------------
# Testes — contrato da ABC
# ---------------------------------------------------------------------------


def test_abc_nao_pode_ser_instanciada_diretamente():
    """IsbnGateway é abstrata — não pode ser instanciada sem implementar 'buscar'."""
    with pytest.raises(TypeError):
        IsbnGateway()  # type: ignore[abstract]


def test_stub_e_subclasse_de_isbn_gateway(gateway_vazio: InMemoryIsbnGateway):
    """O stub concreto deve ser reconhecido como IsbnGateway."""
    assert isinstance(gateway_vazio, IsbnGateway)


def test_stub_implementa_metodo_buscar(gateway_vazio: InMemoryIsbnGateway):
    """O stub deve possuir o método 'buscar' herdado do ABC."""
    assert callable(getattr(gateway_vazio, "buscar", None))


# ---------------------------------------------------------------------------
# Testes — comportamento do método buscar
# ---------------------------------------------------------------------------


async def test_buscar_retorna_none_para_isbn_desconhecido(
    gateway_vazio: InMemoryIsbnGateway,
):
    """ISBN não cadastrado deve retornar None (sem lançar exceção)."""
    result = await gateway_vazio.buscar("0000000000000")
    assert result is None


async def test_buscar_retorna_metadata_para_isbn_conhecido(
    gateway_com_dados: InMemoryIsbnGateway,
):
    """ISBN cadastrado deve retornar o IsbnMetadataOut correspondente."""
    result = await gateway_com_dados.buscar("9788535902778")
    assert result is not None
    assert result.titulo == "Dom Casmurro"


async def test_buscar_retorna_tipo_correto(gateway_com_dados: InMemoryIsbnGateway):
    """O retorno deve ser uma instância de IsbnMetadataOut quando encontrado."""
    result = await gateway_com_dados.buscar("9788535902778")
    assert isinstance(result, IsbnMetadataOut)


async def test_buscar_retorna_todos_os_campos_corretos(
    gateway_com_dados: InMemoryIsbnGateway,
):
    """Todos os campos do metadata retornado devem corresponder ao esperado."""
    result = await gateway_com_dados.buscar("9780132350884")
    assert result is not None
    assert result.titulo == "Clean Code"
    assert result.autores == ["Robert C. Martin"]
    assert result.editora == "Prentice Hall"
    assert result.ano == 2008
    assert result.capa_url is None


async def test_buscar_isbn_diferente_retorna_diferente_metadata(
    gateway_com_dados: InMemoryIsbnGateway,
):
    """ISBNs distintos devem retornar metadados distintos."""
    result_a = await gateway_com_dados.buscar("9788535902778")
    result_b = await gateway_com_dados.buscar("9780132350884")
    assert result_a is not result_b
    assert result_a.titulo != result_b.titulo


async def test_buscar_isbn_inexistente_entre_dados_conhecidos_retorna_none(
    gateway_com_dados: InMemoryIsbnGateway,
):
    """ISBN não presente no gateway deve retornar None mesmo com outros dados cadastrados."""
    result = await gateway_com_dados.buscar("9999999999999")
    assert result is None


# ---------------------------------------------------------------------------
# Testes — campos do IsbnMetadataOut (schema de retorno)
# ---------------------------------------------------------------------------


async def test_metadata_out_campos_opcionais_podem_ser_none():
    """IsbnMetadataOut com todos os campos None deve ser válido."""
    metadata = IsbnMetadataOut()
    assert metadata.titulo is None
    assert metadata.autores is None
    assert metadata.editora is None
    assert metadata.ano is None
    assert metadata.capa_url is None


async def test_metadata_out_retornado_com_campos_parciais():
    """IsbnMetadataOut pode ser retornado com apenas alguns campos preenchidos."""
    gateway = InMemoryIsbnGateway(
        data={"123": IsbnMetadataOut(titulo="Apenas Título")}
    )
    result = await gateway.buscar("123")
    assert result is not None
    assert result.titulo == "Apenas Título"
    assert result.autores is None
    assert result.editora is None
