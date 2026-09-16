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
