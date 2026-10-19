"""
Testes E2E — US-028: Catálogo público de obras (OPAC)
Casos: OPAC-E2E-001 a OPAC-E2E-009

Cobre:
  - GET /api/obras/publico responde 200 sem header Authorization
  - Busca única `q` encontra por título, autor OU categoria (case-insensitive)
  - `%` e `_` no termo são tratados como literais
  - Badge `disponivel` reflete o estado dos exemplares
  - Obra só com exemplares baixados (ou sem exemplares) não aparece (D3)
  - Paginação retorna `total` correto e páginas disjuntas ordenadas por título
  - Payload sem campos sensíveis
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.st_08_opac.conftest import exemplar_factory, obra_factory

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _marcador() -> str:
    """Prefixo único para isolar as buscas de cada teste."""
    return f"opac{uuid.uuid4().hex[:8]}"


async def _buscar(client: AsyncClient, **params) -> dict:
    response = await client.get("/api/obras/publico", params=params)
    assert response.status_code == 200, response.text
    return response.json()


# ─── OPAC-E2E-001 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_001_catalogo_responde_sem_authorization(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-001 — /api/obras/publico é público."""
    tag = _marcador()
    obra = await obra_factory(db_session, titulo=f"{tag} Livro Público")
    await exemplar_factory(db_session, obra_id=obra.id)

    response = await client.get("/api/obras/publico", params={"q": tag})

    assert response.status_code == 200
    assert response.json()["total"] == 1


# ─── OPAC-E2E-002 ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("campo", ["titulo", "autor", "categoria"])
async def test_opac_e2e_002_busca_encontra_por_titulo_autor_ou_categoria(
    client: AsyncClient, db_session: AsyncSession, campo: str
) -> None:
    """OPAC-E2E-002 — o termo único casa com qualquer um dos três campos (OR)."""
    tag = _marcador()
    kwargs = {
        "titulo": {"titulo": f"Título {tag}"},
        "autor": {"autores": [f"Autora {tag}"]},
        "categoria": {"categoria": f"Categoria {tag}"},
    }[campo]
    obra = await obra_factory(db_session, **kwargs)
    await exemplar_factory(db_session, obra_id=obra.id)

    body = await _buscar(client, q=tag.upper())

    assert [item["id"] for item in body["items"]] == [str(obra.id)]


# ─── OPAC-E2E-003 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_003_curingas_do_termo_sao_literais(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-003 — `%` no termo não vira curinga."""
    tag = _marcador()
    com_percentual = await obra_factory(db_session, titulo=f"{tag} 100% Real")
    sem_percentual = await obra_factory(db_session, titulo=f"{tag} 100 Real")
    for obra in (com_percentual, sem_percentual):
        await exemplar_factory(db_session, obra_id=obra.id)

    body = await _buscar(client, q=f"{tag} 100%")

    assert [item["id"] for item in body["items"]] == [str(com_percentual.id)]


# ─── OPAC-E2E-004 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_004_badge_reflete_estado_dos_exemplares(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-004 — disponivel=true com um exemplar livre; false se todos emprestados."""
    tag = _marcador()
    livre = await obra_factory(db_session, titulo=f"{tag} A Livre")
    await exemplar_factory(db_session, obra_id=livre.id, estado="emprestado")
    await exemplar_factory(db_session, obra_id=livre.id, estado="disponivel")
    emprestada = await obra_factory(db_session, titulo=f"{tag} B Emprestada")
    await exemplar_factory(db_session, obra_id=emprestada.id, estado="emprestado")
    await exemplar_factory(db_session, obra_id=emprestada.id, estado="baixado")

    body = await _buscar(client, q=tag)

    disponibilidade = {item["id"]: item["disponivel"] for item in body["items"]}
    assert disponibilidade == {str(livre.id): True, str(emprestada.id): False}


# ─── OPAC-E2E-005 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_005_obra_so_com_baixados_ou_sem_exemplares_nao_aparece(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-005 — D3: obras sem exemplares ativos ficam fora do catálogo."""
    tag = _marcador()
    so_baixados = await obra_factory(db_session, titulo=f"{tag} Baixada")
    await exemplar_factory(db_session, obra_id=so_baixados.id, estado="baixado")
    await obra_factory(db_session, titulo=f"{tag} Sem Exemplares")

    body = await _buscar(client, q=tag)

    assert body["total"] == 0
    assert body["items"] == []


# ─── OPAC-E2E-006 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_006_paginacao_total_e_ordenacao_por_titulo(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-006 — `total` conta todas as obras; páginas são disjuntas e ordenadas."""
    tag = _marcador()
    for letra in "EDCBA":
        obra = await obra_factory(db_session, titulo=f"{tag} {letra}")
        await exemplar_factory(db_session, obra_id=obra.id)

    pagina_1 = await _buscar(client, q=tag, page=1, page_size=2)
    pagina_3 = await _buscar(client, q=tag, page=3, page_size=2)

    assert pagina_1["total"] == 5
    assert [i["titulo"] for i in pagina_1["items"]] == [f"{tag} A", f"{tag} B"]
    assert [i["titulo"] for i in pagina_3["items"]] == [f"{tag} E"]


# ─── OPAC-E2E-007 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_007_payload_sem_campos_sensiveis(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OPAC-E2E-007 — o card expõe só id, título, autores, capa, categoria e disponibilidade."""
    tag = _marcador()
    obra = await obra_factory(db_session, titulo=f"{tag} Card")
    await exemplar_factory(db_session, obra_id=obra.id)

    body = await _buscar(client, q=tag)

    assert set(body) == {"items", "total", "page", "page_size"}
    assert set(body["items"][0]) == {"id", "titulo", "autores", "capa_url", "categoria", "disponivel"}


# ─── OPAC-E2E-008 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_008_page_size_acima_do_limite_retorna_422(client: AsyncClient) -> None:
    """OPAC-E2E-008 — page_size é limitado a 50."""
    response = await client.get("/api/obras/publico", params={"page_size": 51})
    assert response.status_code == 422


# ─── OPAC-E2E-009 ─────────────────────────────────────────────────────────────

async def test_opac_e2e_009_rota_publico_nao_conflita_com_obras_autenticadas(
    client: AsyncClient,
) -> None:
    """OPAC-E2E-009 — /api/obras (balcão) continua exigindo token."""
    response = await client.get("/api/obras")
    assert response.status_code == 401
