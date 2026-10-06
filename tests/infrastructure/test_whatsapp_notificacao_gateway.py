"""
Testes unitários para WhatsAppNotificacaoGateway.

Estratégia: mockar httpx.AsyncClient via monkeypatch/AsyncMock para evitar
chamadas reais à Meta API. Mockar SQLAlchemyNotificacaoLogRepository para
verificar as chamadas a registrar() sem tocar banco.

Cobre:
  - Happy path: POST enviado, log registrado com status='enviado'.
  - Destino vazio: retorna sem enviar e sem registrar log.
  - Destino None: retorna sem enviar e sem registrar log.
  - Retry em 5xx: 3 tentativas, log com status='erro' após esgotamento.
  - Timeout: retry + log de erro após esgotamento.
  - Erro não-retryável (4xx): sem retry, log de erro imediato.
  - RuntimeError no __init__ se WA_TOKEN ou WA_PHONE_NUMBER_ID não definidos.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest

from app.infrastructure.whatsapp_notificacao_gateway import WhatsAppNotificacaoGateway

_LEITOR_ID = uuid4()
_DESTINO = "5511999990001"
_TEMPLATE = "reserva_disponivel"
_PARAMS = {"leitor_id": str(_LEITOR_ID), "nome": "Ana", "titulo": "Dom Casmurro"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_log_repo() -> MagicMock:
    repo = MagicMock()
    repo.registrar = AsyncMock()
    return repo


def _make_gateway(monkeypatch, log_repo=None) -> WhatsAppNotificacaoGateway:
    monkeypatch.setenv("WA_TOKEN", "fake-token")
    monkeypatch.setenv("WA_PHONE_NUMBER_ID", "123456789")
    if log_repo is None:
        log_repo = _make_log_repo()
    return WhatsAppNotificacaoGateway(log_repo=log_repo)


def _make_response(status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# Init — env vars obrigatórias
# ---------------------------------------------------------------------------


class TestInit:
    def test_levanta_runtime_error_sem_wa_token(self, monkeypatch):
        monkeypatch.delenv("WA_TOKEN", raising=False)
        monkeypatch.setenv("WA_PHONE_NUMBER_ID", "123")
        with pytest.raises(RuntimeError, match="WA_TOKEN"):
            WhatsAppNotificacaoGateway(log_repo=_make_log_repo())

    def test_levanta_runtime_error_sem_phone_number_id(self, monkeypatch):
        monkeypatch.setenv("WA_TOKEN", "tok")
        monkeypatch.delenv("WA_PHONE_NUMBER_ID", raising=False)
        with pytest.raises(RuntimeError, match="WA_PHONE_NUMBER_ID"):
            WhatsAppNotificacaoGateway(log_repo=_make_log_repo())

    def test_inicializa_com_variaveis_definidas(self, monkeypatch):
        gw = _make_gateway(monkeypatch)
        assert gw is not None


# ---------------------------------------------------------------------------
# Destino vazio — silêncio total
# ---------------------------------------------------------------------------


class TestDestinoVazio:
    async def test_destino_vazio_retorna_sem_enviar(self, monkeypatch):
        log_repo = _make_log_repo()
        gw = _make_gateway(monkeypatch, log_repo)

        with patch("httpx.AsyncClient") as mock_client_cls:
            await gw.enviar(destino="", template=_TEMPLATE, params=_PARAMS)
            mock_client_cls.assert_not_called()

        log_repo.registrar.assert_not_called()

    async def test_destino_none_retorna_sem_enviar(self, monkeypatch):
        log_repo = _make_log_repo()
        gw = _make_gateway(monkeypatch, log_repo)

        with patch("httpx.AsyncClient") as mock_client_cls:
            await gw.enviar(destino=None, template=_TEMPLATE, params=_PARAMS)  # type: ignore[arg-type]
            mock_client_cls.assert_not_called()

        log_repo.registrar.assert_not_called()


# ---------------------------------------------------------------------------
# Happy path — sucesso no primeiro envio
# ---------------------------------------------------------------------------


class TestEnvioSucesso:
    async def test_envia_post_e_registra_log_enviado(self, monkeypatch):
        log_repo = _make_log_repo()
        gw = _make_gateway(monkeypatch, log_repo)

        mock_response = _make_response(200)
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.infrastructure.whatsapp_notificacao_gateway.httpx.AsyncClient", return_value=mock_client):
            await gw.enviar(destino=_DESTINO, template=_TEMPLATE, params=_PARAMS)

        mock_client.post.assert_awaited_once()
        log_repo.registrar.assert_awaited_once()
        call_kwargs = log_repo.registrar.call_args.kwargs
        assert call_kwargs["status"] == "enviado"
        assert call_kwargs["erro"] is None
        assert call_kwargs["template"] == _TEMPLATE

    async def test_envia_apenas_uma_vez_em_sucesso(self, monkeypatch):
        log_repo = _make_log_repo()
        gw = _make_gateway(monkeypatch, log_repo)

        mock_response = _make_response(200)
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.infrastructure.whatsapp_notificacao_gateway.httpx.AsyncClient", return_value=mock_client):
            await gw.enviar(destino=_DESTINO, template=_TEMPLATE, params=_PARAMS)

        assert mock_client.post.await_count == 1


# ---------------------------------------------------------------------------
# Retry em 5xx
# ---------------------------------------------------------------------------


class TestRetry5xx:
    async def test_tenta_3_vezes_em_5xx_e_registra_erro(self, monkeypatch):
        log_repo = _make_log_repo()
        gw = _make_gateway(monkeypatch, log_repo)

        mock_response = _make_response(500)
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.infrastructure.whatsapp_notificacao_gateway.httpx.AsyncClient", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await gw.enviar(destino=_DESTINO, template=_TEMPLATE, params=_PARAMS)

        assert mock_client.post.await_count == 3
        log_repo.registrar.assert_awaited_once()
        call_kwargs = log_repo.registrar.call_args.kwargs
        assert call_kwargs["status"] == "erro"
        assert call_kwargs["erro"] is not None

    async def test_sucesso_na_segunda_tentativa_registra_enviado(self, monkeypatch):
        log_repo = _make_log_repo()
        gw = _make_gateway(monkeypatch, log_repo)

        fail_response = _make_response(503)
        ok_response = _make_response(200)
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=[fail_response, ok_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.infrastructure.whatsapp_notificacao_gateway.httpx.AsyncClient", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await gw.enviar(destino=_DESTINO, template=_TEMPLATE, params=_PARAMS)

        assert mock_client.post.await_count == 2
        call_kwargs = log_repo.registrar.call_args.kwargs
        assert call_kwargs["status"] == "enviado"


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    async def test_timeout_esgota_retries_e_registra_erro(self, monkeypatch):
        log_repo = _make_log_repo()
        gw = _make_gateway(monkeypatch, log_repo)

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.infrastructure.whatsapp_notificacao_gateway.httpx.AsyncClient", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await gw.enviar(destino=_DESTINO, template=_TEMPLATE, params=_PARAMS)

        assert mock_client.post.await_count == 3
        call_kwargs = log_repo.registrar.call_args.kwargs
        assert call_kwargs["status"] == "erro"


# ---------------------------------------------------------------------------
# Erro 4xx — não retentável
# ---------------------------------------------------------------------------


class TestErro4xx:
    async def test_4xx_nao_retenta_e_registra_erro(self, monkeypatch):
        """4xx não é retentável: deve tentar 1x e registrar erro."""
        log_repo = _make_log_repo()
        gw = _make_gateway(monkeypatch, log_repo)

        mock_response = _make_response(400)
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.infrastructure.whatsapp_notificacao_gateway.httpx.AsyncClient", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await gw.enviar(destino=_DESTINO, template=_TEMPLATE, params=_PARAMS)

        # Apenas 1 tentativa (4xx não é retentável)
        assert mock_client.post.await_count == 1
        mock_sleep.assert_not_called()
        call_kwargs = log_repo.registrar.call_args.kwargs
        assert call_kwargs["status"] == "erro"
