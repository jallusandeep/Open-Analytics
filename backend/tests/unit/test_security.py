import time

import pytest
from jose import JWTError, jwt

from app.config import settings
from app.security import create_access_token, hash_password, verify_password

pytestmark = pytest.mark.unit


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("StrongPassword123!")
    second = hash_password("StrongPassword123!")
    assert first != second
    assert first != "StrongPassword123!"
    assert verify_password("StrongPassword123!", first)
    assert not verify_password("wrong", first)


def test_token_contains_claims_and_expiry_without_mutating_input():
    claims = {"sub": "test-user", "role": "user"}
    token = create_access_token(claims)
    decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
    assert decoded["sub"] == "test-user"
    assert decoded["role"] == "user"
    assert abs(decoded["exp"] - time.time() - settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60) < 5
    assert "exp" not in claims


def test_wrong_signing_key_rejected():
    with pytest.raises(JWTError):
        jwt.decode(create_access_token({"sub": "test-user"}), "wrong-key", algorithms=["HS256"])


def test_expired_token_rejected():
    token = jwt.encode({"sub": "test-user", "exp": 1}, settings.JWT_SECRET_KEY, algorithm="HS256")
    with pytest.raises(JWTError):
        jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
