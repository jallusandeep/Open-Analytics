import pytest
from app.app_access import allowed_apps, serialize_app_access

pytestmark = pytest.mark.unit


def test_legacy_accounts_keep_role_appropriate_defaults():
    assert allowed_apps("user", None) == ["trading", "recom"]
    assert allowed_apps("admin", None) == ["trading", "admin", "recom"]


def test_grants_round_trip_preserves_existing_restrictions():
    stored = serialize_app_access(["existing-restriction"], ["recom"])
    assert "existing-restriction" in stored
    assert allowed_apps("user", stored) == ["recom"]


def test_app_grant_does_not_elevate_user_role():
    assert "admin" not in allowed_apps("user", serialize_app_access([], ["admin", "recom"]))


def test_all_apps_can_be_disabled():
    assert allowed_apps("admin", serialize_app_access([], [])) == []
