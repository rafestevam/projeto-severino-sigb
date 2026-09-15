"""
Testes de integração — ST-05 Reservas e Notificações
Cobre: US-015 (reservar obra), US-016 (notificar reserva disponível)

Regras de negócio centrais:
- Reserva só é permitida quando todos os exemplares da obra estão emprestados
- Um leitor não pode ter mais de uma reserva ativa para a mesma obra
- A posição na fila é determinada pelo created_at (FIFO)
- Notificações (US-016/017) são disparadas de forma assíncrona; os testes verificam
  o registro em notificacao_log, não o envio real ao WhatsApp
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _criar_obra(client: AsyncClient, headers: dict, isbn: str | None = None) -> dict:
    resp = await client.post(
        "/api/obras",
        json={
            "isbn": isbn,
            "titulo": "Obra Para Reserva",
            "autores": ["Autor Teste"],
            "editora": "Editora",
            "ano": 2024,
            "categoria": "Teste",
            "capa_url": None,
        },
        headers=headers,
    )
    return resp.json()


async def _criar_exemplar(client: AsyncClient, obra_id: str, headers: dict) -> dict:
    resp = await client.post(
        f"/api/obras/{obra_id}/exemplares",
        json={"quantidade": 1, "localizacao_estante": "A-01"},
        headers=headers,
    )
    return resp.json()[0]


async def _criar_leitor(client: AsyncClient, headers: dict, cpf: str) -> dict:
    resp = await client.post(
        "/api/leitores",
        json={
            "nome": f"Leitor {cpf[-3:]}",
            "cpf": cpf,
            "telefone": "11999990001",
            "email": f"leitor_{cpf[-4:]}@teste.com",
        },
        headers=headers,
    )
    return resp.json()


async def _fazer_checkout(
    client: AsyncClient, exemplar_id: str, leitor_id: str, headers: dict
) -> dict:
    resp = await client.post(
        "/api/emprestimos",
        json={"exemplar_id": exemplar_id, "leitor_id": leitor_id},
        headers=headers,
    )
    return resp.json()


# ─── US-015: Reservar obra ─────────────────────────────────────────────────────


@pytest.mark.xfail(reason="ST-05 não implementada ainda", strict=False)
async def test_reservar_obra_totalmente_emprestada_cria_reserva(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-015 — POST /api/reservas cria reserva 'aguardando' quando todos os
    exemplares da obra estão emprestados.
    Resposta inclui a posição na fila.
    """
    obra = await _criar_obra(client, auth_headers_operador)
    exemplar = await _criar_exemplar(client, obra["id"], auth_headers_operador)
    leitor_a = await _criar_leitor(client, auth_headers_operador, cpf="11122233344")
    leitor_b = await _criar_leitor(client, auth_headers_operador, cpf="22233344455")

    # Leitor A empresta o único exemplar
    await _fazer_checkout(client, exemplar["id"], leitor_a["id"], auth_headers_operador)

    # Leitor B reserva
    response = await client.post(
        "/api/reservas",
        json={"obra_id": obra["id"], "leitor_id": leitor_b["id"]},
        headers=auth_headers_operador,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "aguardando"
    assert data["obra_id"] == obra["id"]
    assert data["leitor_id"] == leitor_b["id"]
    assert "posicao_fila" in data
    assert data["posicao_fila"] == 1


@pytest.mark.xfail(reason="ST-05 não implementada ainda", strict=False)
async def test_reservar_obra_com_exemplar_disponivel_retorna_erro(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-015 — Tentar reservar obra com exemplar disponível retorna erro orientativo
    (não é necessário reservar — pode emprestar diretamente).
    """
    obra = await _criar_obra(client, auth_headers_operador)
    await _criar_exemplar(client, obra["id"], auth_headers_operador)  # exemplar disponível
    leitor = await _criar_leitor(client, auth_headers_operador, cpf="33344455566")

    response = await client.post(
        "/api/reservas",
        json={"obra_id": obra["id"], "leitor_id": leitor["id"]},
        headers=auth_headers_operador,
    )

    # 409 Conflict ou 422 Unprocessable — implementação define o código
    assert response.status_code in (409, 422)
    assert "disponivel" in response.json()["detail"].lower()


@pytest.mark.xfail(reason="ST-05 não implementada ainda", strict=False)
async def test_leitor_nao_pode_ter_duas_reservas_da_mesma_obra(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-015 — Um leitor não pode ter mais de uma reserva ativa para a mesma obra.
    """
    obra = await _criar_obra(client, auth_headers_operador)
    exemplar = await _criar_exemplar(client, obra["id"], auth_headers_operador)
    leitor_a = await _criar_leitor(client, auth_headers_operador, cpf="44455566677")
    leitor_b = await _criar_leitor(client, auth_headers_operador, cpf="55566677788")

    # Leitor A empresta o exemplar (para ativar a possibilidade de reserva)
    await _fazer_checkout(client, exemplar["id"], leitor_a["id"], auth_headers_operador)

    # Leitor B faz a primeira reserva
    await client.post(
        "/api/reservas",
        json={"obra_id": obra["id"], "leitor_id": leitor_b["id"]},
        headers=auth_headers_operador,
    )

    # Segunda tentativa do leitor B para a mesma obra
    response = await client.post(
        "/api/reservas",
        json={"obra_id": obra["id"], "leitor_id": leitor_b["id"]},
        headers=auth_headers_operador,
    )

    assert response.status_code == 409


@pytest.mark.xfail(reason="ST-05 não implementada ainda", strict=False)
async def test_posicao_fila_e_sequencial_por_created_at(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-015 — A posição na fila é determinada pela ordem de chegada (FIFO via created_at).
    """
    obra = await _criar_obra(client, auth_headers_operador)
    exemplar = await _criar_exemplar(client, obra["id"], auth_headers_operador)
    leitor_a = await _criar_leitor(client, auth_headers_operador, cpf="11199988877")
    leitor_b = await _criar_leitor(client, auth_headers_operador, cpf="22299988877")
    leitor_c = await _criar_leitor(client, auth_headers_operador, cpf="33399988877")

    await _fazer_checkout(client, exemplar["id"], leitor_a["id"], auth_headers_operador)

    resp_b = await client.post(
        "/api/reservas",
        json={"obra_id": obra["id"], "leitor_id": leitor_b["id"]},
        headers=auth_headers_operador,
    )
    resp_c = await client.post(
        "/api/reservas",
        json={"obra_id": obra["id"], "leitor_id": leitor_c["id"]},
        headers=auth_headers_operador,
    )

    assert resp_b.json()["posicao_fila"] == 1
    assert resp_c.json()["posicao_fila"] == 2


@pytest.mark.xfail(reason="ST-05 não implementada ainda", strict=False)
async def test_cancelar_reserva_muda_status_para_expirada(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-015 — DELETE /api/reservas/{id} cancela a reserva.
    """
    obra = await _criar_obra(client, auth_headers_operador)
    exemplar = await _criar_exemplar(client, obra["id"], auth_headers_operador)
    leitor_a = await _criar_leitor(client, auth_headers_operador, cpf="66677788899")
    leitor_b = await _criar_leitor(client, auth_headers_operador, cpf="77788899900")

    await _fazer_checkout(client, exemplar["id"], leitor_a["id"], auth_headers_operador)

    reserva_resp = await client.post(
        "/api/reservas",
        json={"obra_id": obra["id"], "leitor_id": leitor_b["id"]},
        headers=auth_headers_operador,
    )
    reserva_id = reserva_resp.json()["id"]

    response = await client.delete(
        f"/api/reservas/{reserva_id}", headers=auth_headers_operador
    )

    assert response.status_code in (200, 204)

    # Verificar que a reserva não está mais aguardando
    get_resp = await client.get(f"/api/reservas/{reserva_id}", headers=auth_headers_operador)
    if get_resp.status_code == 200:
        assert get_resp.json()["status"] in ("expirada", "cancelada")


# ─── US-016: Notificação de reserva disponível ────────────────────────────────


@pytest.mark.xfail(reason="ST-05 não implementada ainda", strict=False)
async def test_devolucao_enfileira_notificacao_para_proximo_da_fila(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-016 — Ao devolver exemplar com reserva aguardando, uma notificação
    é registrada em notificacao_log para o leitor da fila.
    Não valida o envio real ao WhatsApp — apenas o registro no log.
    """
    obra = await _criar_obra(client, auth_headers_operador)
    exemplar = await _criar_exemplar(client, obra["id"], auth_headers_operador)
    leitor_a = await _criar_leitor(client, auth_headers_operador, cpf="88800011122")
    leitor_b = await _criar_leitor(client, auth_headers_operador, cpf="99900011122")

    await _fazer_checkout(client, exemplar["id"], leitor_a["id"], auth_headers_operador)

    await client.post(
        "/api/reservas",
        json={"obra_id": obra["id"], "leitor_id": leitor_b["id"]},
        headers=auth_headers_operador,
    )

    # Devolver via QR — deve enfileirar notificação
    await client.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar["codigo_qr"]},
        headers=auth_headers_operador,
    )

    # Verificar notificacao_log (endpoint de admin ou via db_session)
    resp_log = await client.get(
        "/api/admin/notificacoes?template=reserva_disponivel",
        headers=auth_headers_operador,
    )
    if resp_log.status_code != 404:
        assert resp_log.status_code == 200
        logs = resp_log.json()
        # Deve existir ao menos um log de notificação para reserva_disponivel
        assert any(
            log.get("template") == "reserva_disponivel" for log in logs.get("items", [])
        )


@pytest.mark.xfail(reason="ST-05 não implementada ainda", strict=False)
async def test_leitor_sem_telefone_nao_bloqueia_devolucao(
    client: AsyncClient, auth_headers_operador: dict
):
    """
    US-016 — Leitor sem telefone cadastrado: notificação é silenciosamente ignorada
    e a devolução ocorre normalmente (sem erro 500).
    """
    obra = await _criar_obra(client, auth_headers_operador)
    exemplar = await _criar_exemplar(client, obra["id"], auth_headers_operador)

    # Leitor sem telefone
    leitor_sem_fone_resp = await client.post(
        "/api/leitores",
        json={
            "nome": "Leitor Sem Fone",
            "cpf": "00011122233",
            "telefone": None,
            "email": "semfone@teste.com",
        },
        headers=auth_headers_operador,
    )
    leitor_sem_fone = leitor_sem_fone_resp.json()

    leitor_com_emprestimo = await client.post(
        "/api/leitores",
        json={
            "nome": "Leitor Com Emprestimo",
            "cpf": "11100022233",
            "telefone": "11999990002",
            "email": "comemprestimo@teste.com",
        },
        headers=auth_headers_operador,
    )
    leitor_com_livro = leitor_com_emprestimo.json()

    await _fazer_checkout(client, exemplar["id"], leitor_com_livro["id"], auth_headers_operador)

    await client.post(
        "/api/reservas",
        json={"obra_id": obra["id"], "leitor_id": leitor_sem_fone["id"]},
        headers=auth_headers_operador,
    )

    # Devolução não deve falhar mesmo sem telefone do reservante
    response = await client.post(
        "/api/emprestimos/devolver-por-qr",
        json={"codigo_qr": exemplar["codigo_qr"]},
        headers=auth_headers_operador,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "devolvido"
