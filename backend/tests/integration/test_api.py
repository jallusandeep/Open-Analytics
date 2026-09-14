import pytest

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("path", ["/", "/health", "/version", "/db-version"])
def test_public_endpoints(api, path):
    response = api.get(path)
    assert response.status_code == 200, response.text
    assert response.json()


def test_database_initialization_is_idempotent(api_container, api):
    result = api_container.exec(["python", "-c", "from app.database import init_database; init_database(); init_database()"])
    assert result.exit_code == 0, result.output
    metadata = api.get("/db-version").json()["metadata"]
    assert any(item["key"] == "schema_version" for item in metadata)


def test_registration_login_and_profile(api, account):
    assert account["role"] == "user"
    response = api.post("/api/v1/auth/login", json={"login_identifier": account["email"], "password": account["password"]})
    assert response.status_code == 200, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    profile = api.get("/api/v1/auth/me", headers=headers)
    assert profile.status_code == 200, profile.text
    assert profile.json()["user"]["email"] == account["email"]
    assert "password_hash" not in profile.text


def test_duplicate_registration_rejected(api, account):
    response = api.post("/api/v1/auth/register", json={key: account[key] for key in ["full_name", "email", "password"]})
    assert response.status_code == 400


def test_wrong_password_rejected(api, account):
    assert api.post("/api/v1/auth/login", json={"login_identifier": account["email"], "password": "wrong"}).status_code == 401


def test_logout_revokes_session(api, account):
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    assert api.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert api.get("/api/v1/auth/me", headers=headers).status_code == 401


@pytest.mark.parametrize("path", ["/api/v1/auth/me", "/api/v1/admin/users", "/api/v1/data/upstox/summary"])
def test_missing_or_invalid_authentication(api, path):
    assert api.get(path).status_code in [401, 403]
    assert api.get(path, headers={"Authorization": "Bearer invalid-token"}).status_code == 401


@pytest.mark.parametrize("path", ["/api/v1/admin/users", "/api/v1/data/upstox/summary", "/api/v1/data/upstox/instruments"])
def test_regular_user_cannot_access_admin_data(api, account, path):
    assert api.get(path, headers={"Authorization": f"Bearer {account['access_token']}"}).status_code == 403


@pytest.mark.parametrize("path", ["/api/v1/admin/users", "/api/v1/data/upstox/summary", "/api/v1/data/upstox/runs", "/api/v1/data/upstox/instruments", "/api/v1/data/upstox/expired-instruments", "/api/v1/data/upstox/schedules"])
def test_admin_read_endpoints(api, admin_headers, path):
    response = api.get(path, headers=admin_headers)
    assert response.status_code == 200, response.text
    if path == "/api/v1/admin/users":
        assert isinstance(response.json()["users"], list)
        assert response.json()["total_records"] >= 1
    else:
        assert response.json()["status"] == "success"


def test_admin_user_crud(api, admin_headers):
    import uuid
    payload = {"full_name": "Managed User", "email": f"managed-{uuid.uuid4().hex}@example.com", "password": "SecurePassword123!", "role": "user"}
    created = api.post("/api/v1/admin/users", json=payload, headers=admin_headers)
    assert created.status_code == 200, created.text
    user_id = created.json()["user_id"]
    updated = api.put(f"/api/v1/admin/users/{user_id}", json={**payload, "full_name": "Updated User", "is_active": False}, headers=admin_headers)
    assert updated.status_code == 200, updated.text
    assert updated.json()["full_name"] == "Updated User"
    assert updated.json()["is_active"] is False
    login = api.post("/api/v1/auth/login", json={"login_identifier": payload["email"], "password": payload["password"]})
    assert login.status_code == 403
    deleted = api.delete(f"/api/v1/admin/users/{user_id}", headers=admin_headers)
    assert deleted.status_code == 200, deleted.text
    listed = api.get("/api/v1/admin/users", params={"search": payload["email"]}, headers=admin_headers)
    assert listed.json()["total_records"] == 0


def test_registration_validation_over_http(api):
    response = api.post("/api/v1/auth/register", json={"full_name": "x", "email": "invalid", "password": "123"})
    assert response.status_code == 422


def test_app_access_persists_and_denies_api_access(api, admin_headers, account):
    import uuid
    created = api.post("/api/v1/auth/register", json={"full_name": "App Access User", "email": f"access-{uuid.uuid4().hex}@example.com", "password": "SecurePassword123!"})
    assert created.status_code == 200, created.text
    account = created.json()
    response = api.put(f"/api/v1/admin/users/{account['user_id']}", headers=admin_headers, json={
        "full_name": account["full_name"], "email": account["email"], "role": "user",
        "app_access": ["trading"], "is_active": True,
    })
    assert response.status_code == 200, response.text
    assert response.json()["app_access"] == ["trading"]
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    profile = api.get("/api/v1/auth/me", headers=headers)
    assert profile.json()["user"]["app_access"] == ["trading"]
    assert api.post("/api/v1/auth/logout", headers=headers).status_code == 200
    login = api.post("/api/v1/auth/login", json={"login_identifier": account["email"], "password": "SecurePassword123!"})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert api.get("/api/v1/users/me", headers=headers).json()["user"]["app_access"] == ["trading"]
    # Data is registered in every backend build. Verify the app-access guard
    # rejects this request before the endpoint's role guard runs.
    denied = api.get("/api/v1/data/upstox/summary", headers=headers)
    assert denied.status_code == 403, denied.text
    assert denied.json()["detail"] == "App access denied"


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 1}, {"page_size": 2001}])
def test_pagination_validation(api, admin_headers, params):
    assert api.get("/api/v1/data/upstox/instruments", params=params, headers=admin_headers).status_code == 422


def test_data_route_contract(api):
    paths = api.get("/openapi.json").json()["paths"]
    assert "/api/v1/data/upstox/summary" in paths
    assert not any("/data-collection/" in path for path in paths)


def test_cors_preflight(api):
    response = api.options("/api/v1/auth/login", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
