import pytest
from fastapi import HTTPException

from app.adapters.api.deps import get_current_user


def test_get_current_user_valid_token():
    # Arrange
    authorization = "Bearer my_super_secret_token"

    # Act
    token = get_current_user(authorization)

    # Assert
    assert token == "my_super_secret_token"


def test_get_current_user_missing_header():
    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Header de Autorização ausente"


def test_get_current_user_invalid_prefix():
    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        get_current_user("Token my_token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Formato de token inválido"


def test_get_current_user_invalid_format():
    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        get_current_user("Bearer")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Formato de token inválido"


def test_get_current_user_too_many_spaces():
    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        get_current_user("Bearer part1 part2")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Formato de token inválido"


# ---------------------------------------------------------------------------
# get_leitor_autenticado (ST-08, decisão D1: vínculo pela claim `email`)
# ---------------------------------------------------------------------------

import base64  # noqa: E402
import json  # noqa: E402
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402

from app.adapters.api.deps import _claims_do_token, get_leitor_autenticado  # noqa: E402
from tests.domain.repositories.conftest import make_leitor  # noqa: E402


def _jwt(claims: dict) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"eyJhbGciOiJub25lIn0.{payload}."


def _patch_repo(retorno):
    repo = MagicMock()
    repo.get_by_email = AsyncMock(return_value=retorno)
    return patch("app.adapters.api.deps.SQLAlchemyLeitorRepository", return_value=repo), repo


def test_claims_do_token_decodifica_payload_sem_padding():
    assert _claims_do_token(_jwt({"email": "a@b.com"})) == {"email": "a@b.com"}


@pytest.mark.parametrize("token", ["test-token-operador", "a.!!!.c", "a.bnVsbA.c"])
def test_claims_do_token_invalido_retorna_401(token):
    with pytest.raises(HTTPException) as exc_info:
        _claims_do_token(token)
    assert exc_info.value.status_code == 401


async def test_get_leitor_autenticado_resolve_pelo_email():
    leitor = make_leitor()
    patcher, repo = _patch_repo(leitor)
    with patcher:
        resultado = await get_leitor_autenticado(
            _jwt({"email": "Maria@Example.com", "email_verified": True}), MagicMock()
        )
    assert resultado is leitor
    repo.get_by_email.assert_awaited_once_with("Maria@Example.com")


async def test_get_leitor_autenticado_403_sem_claim_email():
    patcher, repo = _patch_repo(make_leitor())
    with patcher, pytest.raises(HTTPException) as exc_info:
        await get_leitor_autenticado(_jwt({"sub": "x"}), MagicMock())
    assert exc_info.value.status_code == 403
    repo.get_by_email.assert_not_awaited()


async def test_get_leitor_autenticado_403_sem_leitor_vinculado():
    patcher, _ = _patch_repo(None)
    with patcher, pytest.raises(HTTPException) as exc_info:
        await get_leitor_autenticado(_jwt({"email": "x@y.com", "email_verified": True}), MagicMock())
    assert exc_info.value.status_code == 403


@pytest.mark.parametrize("verificado", [False, None, "true"])
async def test_get_leitor_autenticado_403_com_email_nao_verificado(verificado):
    claims = {"email": "maria@example.com"}
    if verificado is not None:
        claims["email_verified"] = verificado
    patcher, repo = _patch_repo(make_leitor())
    with patcher, pytest.raises(HTTPException) as exc_info:
        await get_leitor_autenticado(_jwt(claims), MagicMock())
    assert exc_info.value.status_code == 403
    repo.get_by_email.assert_not_awaited()
