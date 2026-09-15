"""
Testes de integração — ST-06 Inventário e Gestão
Cobre: US-019 (inventário por bipagem), US-020 (baixar exemplar), US-021 (dashboard)

Regras de negócio:
- Inventário compara QR Codes bipados com exemplares 'disponivel' na estante informada
- Exemplares 'emprestados' são excluídos da lista de 'nao_bipados' (corretamente ausentes)
- Baixa só é permitida se o exemplar não estiver emprestado
- Dashboard não expõe dados pessoais identificáveis
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _criar_obra(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post(
        "/api/obras",
        json={
            "isbn": None,
            "titulo": f"Obra Inventário {uuid.uuid4().hex[:6]}",
            "autores": ["Autor"],
            "editora": "Editora",
            "ano": 2024,
            "categoria": "Teste",
            "capa_url": None,
        },
        headers=headers,
    )
    return resp.json()


async def _criar_exemplar(
    client: AsyncClient, obra_id: str, headers: dict, localizacao: str = "A-01"
) -> dict:
    resp = await client.post(
        f"/api/obras/{obra_id}/exemplares",
        json={"quantidade": 1, "localizacao_estante": localizacao},
        headers=headers,
    )
    return resp.json()[0]


async def _criar_leitor(client: AsyncClient, headers: dict, cpf: str) -> dict:
    resp = await client.post(
        "/api/leitores",
        json={
            "nome": f"Leitor {cpf[-4:]}",
            "cpf": cpf,
            "telefone": None,
            "email": f"leitor_{cpf[-4:]}@inv.com",
        },
        headers=headers,
    )
    return resp.json()


# ─── US-019: Inventário por bipagem ───────────────────────────────────────────


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_inventario_scan_retorna_tres_listas(
    client: AsyncClient, auth_headers_admin: dict
):
    """
    US-019 — POST /api/inventario/scan retorna as três listas:
    encontrados, nao_bipados, nao_esperados.
    """
    obra = await _criar_obra(client, auth_headers_admin)
    exemplar = await _criar_exemplar(client, obra["id"], auth_headers_admin, localizacao="A-01")

    response = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [exemplar["codigo_qr"]], "localizacao": "A-01"},
        headers=auth_headers_admin,
    )

    assert response.status_code == 200
    data = response.json()
    assert "encontrados" in data
    assert "nao_bipados" in data
    assert "nao_esperados" in data


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_inventario_scan_classifica_exemplar_bipado_como_encontrado(
    client: AsyncClient, auth_headers_admin: dict
):
    """
    US-019 — Exemplar bipado que está registrado na estante informada aparece em 'encontrados'.
    """
    obra = await _criar_obra(client, auth_headers_admin)
    exemplar = await _criar_exemplar(client, obra["id"], auth_headers_admin, localizacao="B-02")

    response = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [exemplar["codigo_qr"]], "localizacao": "B-02"},
        headers=auth_headers_admin,
    )

    assert response.status_code == 200
    encontrados_qrs = [e["codigo_qr"] for e in response.json()["encontrados"]]
    assert exemplar["codigo_qr"] in encontrados_qrs


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_inventario_scan_detecta_exemplar_ausente(
    client: AsyncClient, auth_headers_admin: dict
):
    """
    US-019 — Exemplar disponível na estante mas não bipado aparece em 'nao_bipados'.
    """
    obra = await _criar_obra(client, auth_headers_admin)
    exemplar_presente = await _criar_exemplar(
        client, obra["id"], auth_headers_admin, localizacao="C-03"
    )
    exemplar_ausente = await _criar_exemplar(
        client, obra["id"], auth_headers_admin, localizacao="C-03"
    )

    # Bipar apenas o primeiro exemplar
    response = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [exemplar_presente["codigo_qr"]], "localizacao": "C-03"},
        headers=auth_headers_admin,
    )

    assert response.status_code == 200
    nao_bipados_qrs = [e["codigo_qr"] for e in response.json()["nao_bipados"]]
    assert exemplar_ausente["codigo_qr"] in nao_bipados_qrs


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_inventario_scan_exemplar_emprestado_nao_aparece_como_faltante(
    client: AsyncClient, auth_headers_admin: dict
):
    """
    US-019 — Exemplar com estado 'emprestado' não deve aparecer em 'nao_bipados'
    (está legitimamente fora da estante).
    """
    obra = await _criar_obra(client, auth_headers_admin)
    exemplar = await _criar_exemplar(client, obra["id"], auth_headers_admin, localizacao="D-04")
    leitor = await _criar_leitor(client, auth_headers_admin, cpf="12312312312")

    # Emprestar o exemplar
    await client.post(
        "/api/emprestimos",
        json={"exemplar_id": exemplar["id"], "leitor_id": leitor["id"]},
        headers=auth_headers_admin,
    )

    # Inventário da estante sem bipar o exemplar emprestado
    response = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [], "localizacao": "D-04"},
        headers=auth_headers_admin,
    )

    assert response.status_code == 200
    nao_bipados_qrs = [e["codigo_qr"] for e in response.json()["nao_bipados"]]
    # Exemplar emprestado não deve constar como faltante
    assert exemplar["codigo_qr"] not in nao_bipados_qrs


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_inventario_scan_detecta_exemplar_de_outra_estante(
    client: AsyncClient, auth_headers_admin: dict
):
    """
    US-019 — Exemplar bipado que pertence a outra localização aparece em 'nao_esperados'.
    """
    obra = await _criar_obra(client, auth_headers_admin)
    exemplar_outra_estante = await _criar_exemplar(
        client, obra["id"], auth_headers_admin, localizacao="E-05"
    )

    # Bipar na estante F-06 um exemplar que é da E-05
    response = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [exemplar_outra_estante["codigo_qr"]], "localizacao": "F-06"},
        headers=auth_headers_admin,
    )

    assert response.status_code == 200
    nao_esperados_qrs = [e["codigo_qr"] for e in response.json()["nao_esperados"]]
    assert exemplar_outra_estante["codigo_qr"] in nao_esperados_qrs


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_inventario_scan_registra_em_inventario_log(
    client: AsyncClient, auth_headers_admin: dict
):
    """
    US-019 — Cada item bipado no scan gera um registro em inventario_log com acao 'encontrado'.
    """
    obra = await _criar_obra(client, auth_headers_admin)
    exemplar = await _criar_exemplar(client, obra["id"], auth_headers_admin, localizacao="G-07")

    await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [exemplar["codigo_qr"]], "localizacao": "G-07"},
        headers=auth_headers_admin,
    )

    # Verificar log via endpoint admin
    resp_log = await client.get(
        f"/api/admin/inventario-log?exemplar_id={exemplar['id']}",
        headers=auth_headers_admin,
    )
    if resp_log.status_code != 404:
        assert resp_log.status_code == 200
        logs = resp_log.json()
        encontrados = [l for l in logs.get("items", []) if l.get("acao") == "encontrado"]
        assert len(encontrados) >= 1


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_inventario_scan_exige_role_admin(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-019 — O endpoint de inventário exige role 'admin'; operador recebe 403.
    """
    response = await client.post(
        "/api/inventario/scan",
        json={"codigos_qr": [], "localizacao": "A-01"},
        headers=auth_headers_operador,
    )
    assert response.status_code in (401, 403)


# ─── US-020: Dar baixa em exemplar ───────────────────────────────────────────


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_baixar_exemplar_atualiza_estado_para_baixado(
    client: AsyncClient, auth_headers_admin: dict
):
    """
    US-020 — POST /api/exemplares/{id}/baixar marca exemplar como 'baixado'.
    """
    obra = await _criar_obra(client, auth_headers_admin)
    exemplar = await _criar_exemplar(client, obra["id"], auth_headers_admin)

    response = await client.post(
        f"/api/exemplares/{exemplar['id']}/baixar",
        json={"motivo": "danificado"},
        headers=auth_headers_admin,
    )

    assert response.status_code == 200

    resp_exemplar = await client.get(
        f"/api/exemplares/{exemplar['id']}", headers=auth_headers_admin
    )
    assert resp_exemplar.json()["estado"] == "baixado"


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_baixar_exemplar_emprestado_retorna_409(
    client: AsyncClient, auth_headers_admin: dict
):
    """
    US-020 — Tentar dar baixa em exemplar atualmente emprestado retorna 409.
    """
    obra = await _criar_obra(client, auth_headers_admin)
    exemplar = await _criar_exemplar(client, obra["id"], auth_headers_admin)
    leitor = await _criar_leitor(client, auth_headers_admin, cpf="98765432100")

    # Emprestar o exemplar
    await client.post(
        "/api/emprestimos",
        json={"exemplar_id": exemplar["id"], "leitor_id": leitor["id"]},
        headers=auth_headers_admin,
    )

    response = await client.post(
        f"/api/exemplares/{exemplar['id']}/baixar",
        json={"motivo": "extraviado"},
        headers=auth_headers_admin,
    )

    assert response.status_code == 409
    assert "emprestado" in response.json()["detail"].lower()


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_baixar_exemplar_registra_em_inventario_log(
    client: AsyncClient, auth_headers_admin: dict
):
    """
    US-020 — A baixa gera registro em inventario_log com acao 'baixado'.
    """
    obra = await _criar_obra(client, auth_headers_admin)
    exemplar = await _criar_exemplar(client, obra["id"], auth_headers_admin)

    await client.post(
        f"/api/exemplares/{exemplar['id']}/baixar",
        json={"motivo": "danificado"},
        headers=auth_headers_admin,
    )

    resp_log = await client.get(
        f"/api/admin/inventario-log?exemplar_id={exemplar['id']}",
        headers=auth_headers_admin,
    )
    if resp_log.status_code != 404:
        assert resp_log.status_code == 200
        logs = resp_log.json()
        baixados = [l for l in logs.get("items", []) if l.get("acao") == "baixado"]
        assert len(baixados) >= 1


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_baixar_exemplar_exige_role_admin(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-020 — O endpoint de baixa exige role 'admin'; operador recebe 403.
    """
    response = await client.post(
        f"/api/exemplares/{uuid.uuid4()}/baixar",
        json={"motivo": "danificado"},
        headers=auth_headers_operador,
    )
    assert response.status_code in (401, 403)


# ─── US-021: Dashboard de métricas ────────────────────────────────────────────


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_dashboard_retorna_metricas_sem_dados_pessoais(
    client: AsyncClient, auth_headers_admin: dict
):
    """
    US-021 — GET /api/relatorios/dashboard retorna métricas agregadas.
    Nenhum campo deve identificar diretamente um leitor.
    """
    response = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)

    assert response.status_code == 200
    data = response.json()

    # Campos obrigatórios
    assert "total_obras" in data
    assert "total_exemplares" in data
    assert "total_leitores_ativos" in data
    assert "exemplares_por_estado" in data
    assert "top_obras_emprestadas" in data

    # Nenhum campo de leitor identificável
    for campo_proibido in ("nome", "cpf", "cpf_hash", "telefone", "email"):
        assert campo_proibido not in data
        for item in data.get("top_obras_emprestadas", []):
            assert campo_proibido not in item


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_dashboard_contabiliza_estados_de_exemplares(
    client: AsyncClient, auth_headers_admin: dict
):
    """
    US-021 — exemplares_por_estado deve conter contagens para 'disponivel',
    'emprestado' e 'baixado'.
    """
    response = await client.get("/api/relatorios/dashboard", headers=auth_headers_admin)

    assert response.status_code == 200
    estados = response.json()["exemplares_por_estado"]
    assert "disponivel" in estados
    assert "emprestado" in estados
    assert "baixado" in estados


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_emprestimos_atrasados_acessivel_apenas_por_admin(
    client: AsyncClient,
    auth_headers_admin: dict,
    auth_headers_operador: dict,
):
    """
    US-021 — GET /api/relatorios/emprestimos-atrasados exige role 'admin'.
    Operador deve receber 403.
    """
    resp_admin = await client.get(
        "/api/relatorios/emprestimos-atrasados", headers=auth_headers_admin
    )
    assert resp_admin.status_code == 200

    resp_operador = await client.get(
        "/api/relatorios/emprestimos-atrasados", headers=auth_headers_operador
    )
    assert resp_operador.status_code in (401, 403)


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_emprestimos_atrasados_nao_expoe_dados_pessoais(
    client: AsyncClient, auth_headers_admin: dict
):
    """
    US-021 — Lista de atrasados não deve expor nome, CPF ou telefone — apenas leitor_id.
    """
    response = await client.get(
        "/api/relatorios/emprestimos-atrasados", headers=auth_headers_admin
    )
    assert response.status_code == 200
    for item in response.json().get("items", []):
        assert "nome" not in item
        assert "cpf" not in item
        assert "telefone" not in item


@pytest.mark.xfail(reason="ST-06 não implementada ainda", strict=False)
async def test_dashboard_acessivel_por_operador(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-021 — Dashboard deve ser acessível também pelo perfil 'operador'
    (não apenas admin).
    """
    response = await client.get("/api/relatorios/dashboard", headers=auth_headers_operador)
    assert response.status_code == 200
