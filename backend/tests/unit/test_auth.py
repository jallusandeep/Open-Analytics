from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.dependencies import require_admin_or_super_admin, require_super_admin
from app.schemas.auth_schema import ChangePasswordRequest, RegisterRequest, ResetPasswordWithOtpRequest
from app.services import auth_service

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("raw,expected", [(None, None), ("", None), ("abc", None), ("+91 (987) 654-3210", "919876543210"), ("00123", "00123")])
def test_mobile_normalization(raw, expected):
    assert auth_service.normalize_mobile_number(raw) == expected


def test_generated_identifiers_have_expected_format():
    login_id = auth_service.generate_candidate_login_id()
    assert len(login_id) == 10
    assert login_id[:5].isdigit()
    assert all(char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for char in login_id[5:])
    otp = auth_service.generate_forgot_password_otp()
    assert len(otp) == 6 and otp.isdigit()


def test_login_id_collision_retries(monkeypatch):
    candidates = iter(["11111AAAAA", "22222BBBBB"])
    monkeypatch.setattr(auth_service, "generate_candidate_login_id", lambda: next(candidates))
    connection = Mock()
    connection.execute.return_value.fetchone.side_effect = [("existing",), None]
    assert auth_service.generate_unique_login_id(connection) == "22222BBBBB"
    assert connection.execute.call_count == 2


def test_login_id_collision_exhaustion():
    connection = Mock()
    connection.execute.return_value.fetchone.return_value = ("existing",)
    with pytest.raises(HTTPException) as error:
        auth_service.generate_unique_login_id(connection)
    assert error.value.status_code == 500
    assert connection.execute.call_count == auth_service.LOGIN_ID_GENERATION_ATTEMPTS


@pytest.mark.parametrize("role", ["admin", "super_admin"])
def test_admin_roles_allowed(role):
    user = {"role": role}
    assert require_admin_or_super_admin(user) is user


@pytest.mark.parametrize("dependency,role", [(require_admin_or_super_admin, "user"), (require_super_admin, "user"), (require_super_admin, "admin")])
def test_insufficient_roles_rejected(dependency, role):
    with pytest.raises(HTTPException) as error:
        dependency({"role": role})
    assert error.value.status_code == 403


def test_super_admin_allowed():
    user = {"role": "super_admin"}
    assert require_super_admin(user) is user


@pytest.mark.parametrize("password,confirmation", [("newpass", "different"), ("oldpass", "oldpass")])
def test_invalid_password_changes(password, confirmation):
    with pytest.raises(ValidationError):
        ChangePasswordRequest(current_password="oldpass", new_password=password, confirm_password=confirmation)


def test_password_reset_requires_matching_passwords():
    with pytest.raises(ValidationError):
        ResetPasswordWithOtpRequest(login_identifier="test-user", otp="123456", new_password="newpass", confirm_password="different")


@pytest.mark.parametrize("field,value", [("full_name", "x"), ("email", "invalid"), ("password", "123")])
def test_registration_validation(field, value):
    payload = {"full_name": "Test User", "email": "test@example.com", "password": "secure123"}
    payload[field] = value
    with pytest.raises(ValidationError):
        RegisterRequest(**payload)
